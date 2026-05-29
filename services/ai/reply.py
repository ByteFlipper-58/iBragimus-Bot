"""High-level helper: turn an incoming message into an AI reply."""

from database.repository import BotRepository
from services.ai.config import get_ai_config
from services.ai.registry import get_ai_provider


def _build_chat_history(logs: list[dict]) -> list[dict[str, str]]:
    """Convert stored conversation logs into provider-ready turns."""
    history: list[dict[str, str]] = []
    for entry in logs:
        user_text = entry.get("message_text")
        reply_text = entry.get("reply_text")
        if user_text:
            history.append({"role": "user", "content": user_text})
        if reply_text:
            history.append({"role": "assistant", "content": reply_text})
    return history


async def _load_chat_history(
    repo: BotRepository,
    settings_map: dict[str, str] | None,
    chat_id: int | None,
) -> list[dict[str, str]] | None:
    """Optionally load short conversation context for the AI prompt."""
    if settings_map is None or chat_id is None:
        return None

    if settings_map.get("ai_context_enabled", "1") != "1":
        return None

    try:
        limit = max(0, int(settings_map.get("ai_context_limit", "5")))
    except (ValueError, TypeError):
        limit = 5

    if limit <= 0:
        return None

    logs = await repo.logs.get_chat_history(chat_id, limit=limit)
    return _build_chat_history(logs)


async def generate_reply(
    repo: BotRepository,
    *,
    message_text: str,
    system_prompt: str,
    settings_map: dict[str, str] | None = None,
    chat_id: int | None = None,
) -> str | None:
    """Resolve the AI provider, build context, and request a reply."""
    config = await get_ai_config(repo, settings_map=settings_map)
    provider = get_ai_provider(config)
    chat_history = await _load_chat_history(repo, settings_map, chat_id)
    return await provider.generate_reply(
        message_text=message_text,
        system_prompt=system_prompt,
        chat_history=chat_history,
    )
