"""Provider-agnostic AI configuration resolution.

``AIConfig`` describes the active provider, its model and API key. The active
configuration is built from admin-stored settings, falling back to the
environment-driven ``config.settings`` defaults. The dataclass is frozen so it
can be hashed and used as a cache key by the provider registry.
"""

from dataclasses import dataclass

from config import settings
from database.repository import BotRepository

AI_PROVIDERS: frozenset[str] = frozenset({"openai", "anthropic", "google"})

AI_PROVIDER_LABELS: dict[str, str] = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
}


@dataclass(frozen=True)
class AIConfig:
    """Immutable snapshot of the active AI provider settings."""

    provider: str
    api_key: str | None
    model_name: str


def _clean_optional(value: str | None) -> str | None:
    """Drop empty/placeholder values so callers see ``None`` for missing keys."""
    if not value:
        return None
    value = value.strip()
    if not value or "YOUR_" in value:
        return None
    return value


def _normalize_provider(raw_provider: str | None) -> str:
    """Normalize a provider identifier and fall back to ``google``."""
    candidate = (raw_provider or settings.AI_PROVIDER or "google").strip().lower()
    if candidate == "gemini":
        candidate = "google"
    if candidate not in AI_PROVIDERS:
        candidate = "google"
    return candidate


_DEFAULTS: dict[str, tuple[str | None, str]] = {
    "openai": (settings.OPENAI_API_KEY, settings.OPENAI_MODEL),
    "anthropic": (settings.ANTHROPIC_API_KEY, settings.ANTHROPIC_MODEL),
    "google": (settings.GEMINI_API_KEY, settings.GEMINI_MODEL),
}


async def get_ai_config(
    repo: BotRepository,
    settings_map: dict[str, str] | None = None,
) -> AIConfig:
    """Build the active AI config.

    When ``settings_map`` is provided (already loaded via ``settings.all()``),
    no extra database queries are issued. Otherwise the individual settings are
    fetched on demand.
    """

    async def _read(key: str, default: str | None = None) -> str | None:
        if settings_map is not None:
            return settings_map.get(key, default)
        return await repo.settings.get(key, default)

    provider = _normalize_provider(_clean_optional(await _read("ai_provider", None)))
    default_key, default_model = _DEFAULTS[provider]

    api_key = await _read(f"{provider}_api_key", None)
    model_name = await _read(f"{provider}_model", default_model)

    return AIConfig(
        provider=provider,
        api_key=_clean_optional(api_key) or _clean_optional(default_key),
        model_name=(model_name or default_model).strip(),
    )
