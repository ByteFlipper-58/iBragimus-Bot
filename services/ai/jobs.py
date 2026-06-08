"""Background AI tasks: rolling summary, auto-memory, owner style mining.

These helpers share the same provider as the regular reply path, but each
issues a single "system instruction + user prompt" call without conversation
history. They are intentionally idempotent and safe to skip on errors — the
main reply pipeline must not break because a memory job hiccuped.
"""

from __future__ import annotations

import logging
from datetime import datetime

from database.repository import BotRepository
from services.ai.config import get_ai_config
from services.ai.registry import get_ai_provider

logger = logging.getLogger(__name__)

MAX_CHARS_PER_TURN = 600
MAX_NOTES_AFTER_APPEND = 3000
MAX_SUMMARY_CHARS = 1200
MAX_OWNER_STYLE_CHARS = 1000


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _format_dialog(rows: list[dict], owner_id: int) -> str:
    """Render archived rows as a compact dialog transcript."""
    lines: list[str] = []
    for row in rows:
        text = (row.get("message_text") or "").strip()
        if not text:
            continue
        who = "Я" if row.get("sender_id") == owner_id else "Собеседник"
        lines.append(f"{who}: {_truncate(text, MAX_CHARS_PER_TURN)}")
    return "\n".join(lines)


async def _ask_oneshot(
    repo: BotRepository,
    *,
    settings_map: dict[str, str],
    instructions: str,
    user_prompt: str,
) -> str | None:
    """Issue a single LLM call without any chat history."""
    config = await get_ai_config(repo, settings_map=settings_map)
    if not config.api_key:
        return None
    try:
        provider = get_ai_provider(config)
        return await provider.generate_reply(
            message_text=user_prompt,
            system_prompt=instructions,
            chat_history=None,
        )
    except Exception as exc:
        logger.warning("AI background job failed: %s", exc, exc_info=True)
        return None


# -- Rolling summary ----------------------------------------------------------

SUMMARY_INSTRUCTIONS = (
    "Ты обобщаешь личный диалог в Telegram. Твоя задача — переписать "
    "переписку в один компактный абзац от третьего лица: кто эти люди "
    "друг для друга, о чём общаются, какие договорённости и факты "
    "уже прозвучали, какое сейчас настроение. Без воды, без "
    "приветствий, без советов. Длина: 3–6 коротких предложений. "
    "Если есть предыдущая краткая сводка — учитывай её, но не повторяй дословно."
)


async def update_summary_if_needed(
    repo: BotRepository,
    *,
    settings_map: dict[str, str],
    chat_id: int,
    owner_id: int,
) -> None:
    """Refresh the rolling summary when the chat grew past the threshold.

    Drops messages already summarised, keeps a tail of recent messages out of
    the summary so the live context window has fresh material.
    """
    if settings_map.get("summary_enabled", "1") != "1":
        return

    try:
        threshold = max(10, int(settings_map.get("summary_threshold", "30")))
    except (ValueError, TypeError):
        threshold = 30

    try:
        live_window = max(0, int(settings_map.get("ai_context_limit", "5"))) * 2
    except (ValueError, TypeError):
        live_window = 10
    live_window = max(live_window, 6)

    state = await repo.chat_state.get_state(chat_id)
    cursor = state["summary_up_to_id"]

    rows = await repo.archive.get_messages_after(chat_id, cursor, limit=400)
    # Keep the most recent ``live_window`` messages out of the summary so
    # they remain in the live context window.
    if len(rows) <= live_window + 6:
        return

    to_summarise = rows[: len(rows) - live_window]
    if len(to_summarise) < 6:
        return

    transcript = _format_dialog(to_summarise, owner_id=owner_id)
    if not transcript:
        return

    previous = state["summary"].strip()
    user_prompt_parts: list[str] = []
    if previous:
        user_prompt_parts.append(
            "Предыдущая сводка (используй как фундамент):\n" + previous
        )
    user_prompt_parts.append("Новые сообщения диалога:\n" + transcript)
    user_prompt_parts.append(
        "Перепиши общую краткую сводку (3–6 коротких предложений) с учётом всего."
    )

    summary = await _ask_oneshot(
        repo,
        settings_map=settings_map,
        instructions=SUMMARY_INSTRUCTIONS,
        user_prompt="\n\n".join(user_prompt_parts),
    )
    if not summary:
        return

    new_cursor = to_summarise[-1]["message_id"]
    await repo.chat_state.set_summary(
        chat_id,
        _truncate(summary, MAX_SUMMARY_CHARS),
        new_cursor,
    )
    logger.info(
        "Updated rolling summary for chat=%s (cursor=%s)", chat_id, new_cursor
    )


# -- Auto-memory --------------------------------------------------------------

AUTO_MEMORY_INSTRUCTIONS = (
    "Ты ведёшь короткую заметку о собеседнике для владельца аккаунта. "
    "Из присланного фрагмента диалога выпиши новые устойчивые факты про "
    "собеседника или про отношения между ним и владельцем: имя, кем "
    "приходится, ключевые планы, договорённости, важные предпочтения и "
    "обстоятельства. Игнорируй эмоции момента и одноразовые мелочи. "
    "Если ничего значимого не появилось — ответь ровно одним словом: NONE. "
    "Иначе верни 1–4 коротких пункта без нумерации, по одному на строку, "
    "не повторяй уже известное из существующей заметки."
)


def _merge_notes(existing: str, additions: str) -> str | None:
    """Combine the existing note with a fresh batch of bullet additions."""
    existing = (existing or "").strip()
    cleaned_lines: list[str] = []
    for raw_line in (additions or "").splitlines():
        line = raw_line.strip(" \t-•*·").strip()
        if not line or line.upper() == "NONE":
            continue
        if existing and line.lower() in existing.lower():
            continue
        if line in cleaned_lines:
            continue
        cleaned_lines.append(line)

    if not cleaned_lines:
        return None

    joined_new = "\n".join(f"- {line}" for line in cleaned_lines)
    if not existing:
        merged = joined_new
    else:
        merged = f"{existing}\n{joined_new}"

    return _truncate(merged, MAX_NOTES_AFTER_APPEND)


async def update_auto_memory_if_needed(
    repo: BotRepository,
    *,
    settings_map: dict[str, str],
    chat_id: int,
    owner_id: int,
) -> None:
    """Extract durable facts from new messages and append them to ``chat_notes``."""
    if settings_map.get("auto_memory_enabled", "1") != "1":
        return

    try:
        every_n = max(4, int(settings_map.get("auto_memory_every_n", "10")))
    except (ValueError, TypeError):
        every_n = 10

    state = await repo.chat_state.get_state(chat_id)
    rows = await repo.archive.get_messages_after(
        chat_id, state["last_auto_memory_id"], limit=200
    )
    if len(rows) < every_n:
        return

    transcript = _format_dialog(rows, owner_id=owner_id)
    if not transcript:
        return

    existing_notes = await repo.chat_notes.get(chat_id)

    user_prompt_parts: list[str] = []
    if existing_notes.strip():
        user_prompt_parts.append(
            "Уже известно про собеседника:\n" + existing_notes.strip()
        )
    user_prompt_parts.append("Свежий фрагмент диалога:\n" + transcript)
    user_prompt_parts.append(
        "Какие НОВЫЕ устойчивые факты стоит запомнить? Помни про NONE."
    )

    raw = await _ask_oneshot(
        repo,
        settings_map=settings_map,
        instructions=AUTO_MEMORY_INSTRUCTIONS,
        user_prompt="\n\n".join(user_prompt_parts),
    )

    last_id = rows[-1]["message_id"]

    if raw and raw.strip().upper() != "NONE":
        merged = _merge_notes(existing_notes, raw)
        if merged is not None and merged != existing_notes:
            await repo.chat_notes.set(chat_id, merged)
            logger.info("Auto-memory appended new facts for chat=%s", chat_id)

    # Always advance the cursor so we do not re-process the same window even
    # when the model returned NONE.
    await repo.chat_state.set_last_auto_memory_id(chat_id, last_id)


# -- Owner writing style ------------------------------------------------------

OWNER_STYLE_INSTRUCTIONS = (
    "Тебе показывают подборку настоящих сообщений ОДНОГО человека из его "
    "личной переписки. Опиши его манеру письма так, чтобы другой текст можно "
    "было сгенерировать в этом же стиле: длина типичных сообщений, "
    "эмодзи и знаки, обращение на ты/вы, любимые словечки, мат, скобки, "
    "сокращения, какой регистр (нижний/со заглавной), как обрывает фразы. "
    "Не пересказывай содержание сообщений, только стиль. "
    "Верни 4–8 коротких пунктов через перенос строки."
)

OWNER_STYLE_REFRESH_AFTER_HOURS = 24


def _hours_since(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        ts = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None
    return (datetime.utcnow() - ts).total_seconds() / 3600


async def refresh_owner_style_if_needed(
    repo: BotRepository,
    *,
    settings_map: dict[str, str],
    owner_id: int,
    force: bool = False,
) -> None:
    """Mine the owner's own messages for stylistic guidance, at most once a day."""
    last_run = settings_map.get("owner_style_updated_at", "")
    age = _hours_since(last_run) if last_run else None
    if not force and age is not None and age < OWNER_STYLE_REFRESH_AFTER_HOURS:
        return

    rows = await repo.archive.get_recent_outgoing_by_owner(owner_id, limit=80)
    if len(rows) < 12:
        return

    sample = "\n".join(
        f"- {_truncate((row.get('message_text') or '').strip(), 240)}"
        for row in rows
        if (row.get("message_text") or "").strip()
    )
    if not sample:
        return

    style = await _ask_oneshot(
        repo,
        settings_map=settings_map,
        instructions=OWNER_STYLE_INSTRUCTIONS,
        user_prompt="Сообщения владельца:\n" + sample,
    )
    if not style:
        return

    style_clean = _truncate(style, MAX_OWNER_STYLE_CHARS)
    await repo.settings.set("owner_style", style_clean)
    await repo.settings.set(
        "owner_style_updated_at",
        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    )
    # Refresh the in-memory map so the same request can use the new style.
    settings_map["owner_style"] = style_clean
    logger.info("Refreshed owner style profile.")
