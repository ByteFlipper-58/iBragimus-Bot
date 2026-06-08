"""High-level helper: turn an incoming message into an AI reply.

The reply pipeline now goes beyond the raw user prompt and feeds the model
several layers of context so it can convincingly impersonate the account
owner instead of acting like a generic assistant:

* full back-and-forth recovered from ``business_messages`` (including
  incoming messages that did not trigger a reply);
* an "about me" block describing the owner (``owner_bio`` setting);
* free-form notes attached to the current contact (``chat_notes``);
* the contact's display name and the current date/time so the model can
  ground time-sensitive answers.
"""

from datetime import datetime

from config import settings as app_settings
from database.repository import BotRepository
from services.ai.config import get_ai_config
from services.ai.registry import get_ai_provider

_DAYS_OF_WEEK_RU = (
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
)


def _build_history_from_archive(
    rows: list[dict],
    *,
    owner_id: int,
    current_message_id: int | None,
) -> list[dict[str, str]]:
    """Convert archived business messages into provider-ready turns.

    Messages from the owner become ``assistant`` turns, everything else is
    treated as ``user``. Consecutive same-role turns are merged so the
    history alternates cleanly (Anthropic in particular expects strict
    alternation starting from ``user``).
    """
    turns: list[dict[str, str]] = []
    for row in rows:
        if current_message_id is not None and row.get("message_id") == current_message_id:
            continue
        text = (row.get("message_text") or "").strip()
        if not text:
            continue
        role = "assistant" if row.get("sender_id") == owner_id else "user"
        turns.append({"role": role, "content": text})

    merged: list[dict[str, str]] = []
    for turn in turns:
        if merged and merged[-1]["role"] == turn["role"]:
            merged[-1]["content"] = f"{merged[-1]['content']}\n{turn['content']}"
        else:
            merged.append(dict(turn))

    # Anthropic refuses histories that start with an assistant turn; the
    # other providers tolerate it but the conversation reads better when
    # the first turn is the contact's message anyway.
    while merged and merged[0]["role"] != "user":
        merged.pop(0)

    return merged


async def _load_chat_history(
    repo: BotRepository,
    settings_map: dict[str, str] | None,
    chat_id: int | None,
    *,
    owner_id: int,
    current_message_id: int | None,
    summary_up_to_id: int = 0,
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

    # ``limit`` is expressed as exchanges in the admin UI. Each exchange is
    # roughly two messages (contact + owner reply), so we fetch a bit more
    # raw rows and let the merger collapse them into clean turns.
    raw_rows = await repo.archive.get_recent_for_chat(
        chat_id, limit=max(2 * limit + 1, limit + 1)
    )
    # Drop messages that are already covered by the rolling summary so we do
    # not feed the same content to the model twice.
    if summary_up_to_id:
        raw_rows = [
            row for row in raw_rows
            if (row.get("message_id") or 0) > summary_up_to_id
        ]
    history = _build_history_from_archive(
        raw_rows,
        owner_id=owner_id,
        current_message_id=current_message_id,
    )
    return history or None


def _format_datetime(now: datetime) -> str:
    """Return a human-friendly Russian date string for the system prompt."""
    weekday = _DAYS_OF_WEEK_RU[now.weekday()]
    return f"{now.strftime('%Y-%m-%d %H:%M')} ({weekday})"


def _compose_system_prompt(
    base_prompt: str,
    *,
    owner_bio: str,
    owner_style: str,
    sender_name: str | None,
    sender_id: int | None,
    chat_notes: str,
    chat_summary: str,
    now: datetime,
) -> str:
    """Append per-conversation context to the user-defined system prompt."""
    sections: list[str] = [(base_prompt or "").strip()]

    sections.append(f"[Сейчас]: {_format_datetime(now)}.")

    if sender_name or sender_id is not None:
        if sender_name and sender_id is not None:
            sender_line = f"{sender_name} (id {sender_id})"
        elif sender_name:
            sender_line = sender_name
        else:
            sender_line = f"id {sender_id}"
        sections.append(f"[С тобой сейчас пишет]: {sender_line}.")

    cleaned_bio = (owner_bio or "").strip()
    if cleaned_bio:
        sections.append(
            "[О тебе самом — это факты про владельца аккаунта, "
            "от чьего имени ты отвечаешь]:\n" + cleaned_bio
        )

    cleaned_style = (owner_style or "").strip()
    if cleaned_style:
        sections.append(
            "[Манера письма, в которой ты отвечаешь — это типичный стиль "
            "владельца, подсмотренный из его настоящих сообщений. Подражай ему]:\n"
            + cleaned_style
        )

    cleaned_summary = (chat_summary or "").strip()
    if cleaned_summary:
        sections.append(
            "[Краткое содержание прошлых разговоров с этим собеседником "
            "(для памяти, не пересказывай дословно)]:\n" + cleaned_summary
        )

    cleaned_notes = (chat_notes or "").strip()
    if cleaned_notes:
        sections.append(
            "[Что ты помнишь именно про этого собеседника]:\n" + cleaned_notes
        )

    return "\n\n".join(section for section in sections if section)


async def _resolve_owner_bio(
    repo: BotRepository,
    settings_map: dict[str, str] | None,
) -> str:
    """Fetch the owner's "about me" text without an extra DB hit when possible."""
    if settings_map is not None:
        return settings_map.get("owner_bio", "") or ""
    return (await repo.settings.get("owner_bio", "")) or ""


async def _resolve_chat_notes(
    repo: BotRepository,
    chat_id: int | None,
) -> str:
    """Return per-contact notes for ``chat_id`` (empty string when absent)."""
    if chat_id is None:
        return ""
    try:
        return await repo.chat_notes.get(chat_id)
    except Exception:
        # Notes are best-effort enrichment; never let a DB hiccup kill the reply.
        return ""


async def generate_reply(
    repo: BotRepository,
    *,
    message_text: str,
    system_prompt: str,
    settings_map: dict[str, str] | None = None,
    chat_id: int | None = None,
    sender_id: int | None = None,
    sender_name: str | None = None,
    current_message_id: int | None = None,
    now: datetime | None = None,
) -> str | None:
    """Resolve the AI provider, build context, and request a reply.

    The optional ``sender_*``, ``current_message_id`` and ``now`` arguments
    let the caller pass per-message metadata that the helper folds into the
    system prompt and uses to deduplicate the just-archived incoming message
    from the conversation history.
    """
    config = await get_ai_config(repo, settings_map=settings_map)
    provider = get_ai_provider(config)

    owner_id = app_settings.ADMIN_ID

    chat_state = None
    if chat_id is not None:
        try:
            chat_state = await repo.chat_state.get_state(chat_id)
        except Exception:
            chat_state = None
    summary_up_to_id = (chat_state or {}).get("summary_up_to_id") or 0
    chat_summary = (chat_state or {}).get("summary") or ""

    chat_history = await _load_chat_history(
        repo,
        settings_map,
        chat_id,
        owner_id=owner_id,
        current_message_id=current_message_id,
        summary_up_to_id=summary_up_to_id,
    )

    owner_bio = await _resolve_owner_bio(repo, settings_map)
    owner_style = (settings_map or {}).get("owner_style", "") if settings_map else (
        await repo.settings.get("owner_style", "") or ""
    )
    chat_notes = await _resolve_chat_notes(repo, chat_id)

    enriched_prompt = _compose_system_prompt(
        system_prompt,
        owner_bio=owner_bio,
        owner_style=owner_style,
        sender_name=sender_name,
        sender_id=sender_id,
        chat_notes=chat_notes,
        chat_summary=chat_summary,
        now=now or datetime.now(),
    )

    return await provider.generate_reply(
        message_text=message_text,
        system_prompt=enriched_prompt,
        chat_history=chat_history,
    )
