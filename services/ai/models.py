"""Listing of available models per provider used by the admin UI."""

import logging

from anthropic import AsyncAnthropic
from google import genai
from openai import AsyncOpenAI

from services.ai.config import AIConfig

logger = logging.getLogger(__name__)

_NON_TEXT_TOKENS = ("embedding", "moderation", "audio", "image", "tts", "whisper")
_PRIORITY_TOKENS = ("gpt", "claude", "gemini")


def _extract_model_id(model: object) -> str | None:
    """Pull the canonical model identifier out of a provider response object."""
    value = getattr(model, "id", None) or getattr(model, "name", None)
    if not value:
        return None
    model_id = str(value).strip()
    if model_id.startswith("models/"):
        model_id = model_id.split("/", 1)[1]
    return model_id or None


def _rank_model(model_id: str) -> tuple[int, str]:
    """Sort known chat models first, then any usable models, then the rest."""
    lowered = model_id.lower()
    if any(token in lowered for token in _NON_TEXT_TOKENS):
        return (3, lowered)
    if any(token in lowered for token in _PRIORITY_TOKENS):
        return (0, lowered)
    return (1, lowered)


def _supports_text_generation(provider: str, model: object, model_id: str) -> bool:
    """Return whether a model can generate plain text replies."""
    lowered = model_id.lower()
    if provider == "openai":
        return not any(token in lowered for token in _NON_TEXT_TOKENS)
    if provider == "google":
        supported_actions = getattr(model, "supported_actions", None)
        if not supported_actions:
            return True
        actions = {
            "".join(ch for ch in str(getattr(action, "value", action)).lower() if ch.isalnum())
            for action in supported_actions
        }
        return any("generatecontent" in action for action in actions)
    return True


async def _list_openai(config: AIConfig) -> list[str]:
    client = AsyncOpenAI(api_key=config.api_key)
    ids: list[str] = []
    async for model in client.models.list():
        model_id = _extract_model_id(model)
        if model_id and _supports_text_generation(config.provider, model, model_id):
            ids.append(model_id)
    return ids


async def _list_anthropic(config: AIConfig) -> list[str]:
    client = AsyncAnthropic(api_key=config.api_key)
    ids: list[str] = []
    async for model in client.models.list(limit=100):
        model_id = _extract_model_id(model)
        if model_id and _supports_text_generation(config.provider, model, model_id):
            ids.append(model_id)
    return ids


async def _list_google(config: AIConfig) -> list[str]:
    client = genai.Client(api_key=config.api_key)
    ids: list[str] = []
    pager = await client.aio.models.list()
    async for model in pager:
        model_id = _extract_model_id(model)
        if model_id and _supports_text_generation(config.provider, model, model_id):
            ids.append(model_id)
    return ids


_LISTERS = {
    "openai": _list_openai,
    "anthropic": _list_anthropic,
    "google": _list_google,
}


async def list_available_models(config: AIConfig, limit: int = 20) -> list[str]:
    """Return model ids available for the selected provider.

    The currently selected ``config.model_name`` is always present at the top
    of the returned list, even if the provider does not enumerate it.
    """
    model_ids: list[str] = []

    if config.api_key:
        lister = _LISTERS.get(config.provider)
        if lister is not None:
            try:
                model_ids = await lister(config)
            except Exception as e:
                logger.warning(
                    "Could not fetch %s model list. Falling back to the current model: %s",
                    config.provider,
                    e,
                )
                model_ids = []

    model_ids.append(config.model_name)
    unique_ids = sorted({model_id for model_id in model_ids if model_id}, key=_rank_model)
    if config.model_name in unique_ids:
        unique_ids.remove(config.model_name)
        unique_ids.insert(0, config.model_name)
    return unique_ids[:limit]
