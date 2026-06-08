"""Auto-reply pipeline for Telegram Business messages.

The handler does three things in order:

* archive every incoming/outgoing message so the AI sees the full back-and-forth;
* let the owner toggle a per-chat pause through configurable stop/resume words;
* schedule a debounced AI reply so a burst of consecutive messages from the
  same contact produces a single, contextual answer instead of one reply per
  line. After delivering a reply we kick off cheap background jobs (rolling
  summary, auto-memory, owner-style profiling) that further enrich future
  responses.
"""

import asyncio
import logging

from aiogram import Bot, Router
from aiogram.types import Message

from config import settings
from database.repository import BotRepository
from services.ai import generate_reply
from services.ai.jobs import (
    refresh_owner_style_if_needed,
    update_auto_memory_if_needed,
    update_summary_if_needed,
)
from services.business import cache_message_media, skip_reply_reason
from services.business.skip_policy import (
    SKIP_AI_DISABLED,
    SKIP_BLACKLISTED,
    SKIP_OWNER_ACTIVE,
    SKIP_PAUSED,
    SKIP_TOXIC,
)

logger = logging.getLogger(__name__)
router = Router(name="business_messages")

DEFAULT_SYSTEM_PROMPT = (
    "Ты отвечаешь в личной переписке Telegram ОТ ИМЕНИ владельца аккаунта, "
    "от первого лица. Ты — это он сам. Пиши так, как написал бы живой человек "
    "в мессенджере: коротко, по-человечески, без формальностей.\n\n"
    "Жёсткие правила:\n"
    "1. Отвечай ОДНИМ сообщением — одним готовым ответом, без вариантов и "
    "альтернатив.\n"
    "2. НИКОГДА не пиши «вот несколько вариантов», «варианты ответа», "
    "«можно ответить так», списков с пунктами, тире или маркерами.\n"
    "3. НИКОГДА не объясняй и не комментируй свой ответ, не давай советов "
    "(«лучше сохранять спокойствие», «совет:» и т.п.). Только сам ответ.\n"
    "4. Не используй Markdown, звёздочки, заголовки, эмодзи списков. "
    "Обычный текст, как в чате.\n"
    "5. Пиши на том же языке, на котором пишет собеседник.\n"
    "6. Если не знаешь конкретный факт о владельце (время поезда, планы, "
    "адрес), не выдумывай — отвечай уклончиво, как живой человек: «уточню», "
    "«гляну и скажу», «не помню точно».\n"
    "7. Длина — обычно 1–2 короткие фразы. Без воды."
)

# Debounce state. The bot keeps one timer task per chat, plus a snapshot of the
# most recent message in that chat so the deferred reply targets the latest
# turn. Everything is in-memory: a process restart simply drops pending timers,
# which is fine because the messages themselves are already archived.
_DEBOUNCE_TASKS: dict[int, asyncio.Task] = {}
_DEBOUNCE_PAYLOADS: dict[int, dict] = {}
_DEBOUNCE_LOCK = asyncio.Lock()


def _parse_int(raw_value: str | None, *, default: int, lo: int = 0, hi: int = 86400) -> int:
    """Parse a non-negative integer setting, clamped to ``[lo, hi]``."""
    try:
        value = int(raw_value if raw_value is not None else default)
    except (ValueError, TypeError) as e:
        logger.warning("Invalid integer setting %r: %s", raw_value, e)
        return default
    return max(lo, min(hi, value))


async def _log_skip(
    repo: BotRepository,
    *,
    skip_reason: str,
    connection_id: str,
    chat_id: int,
    sender_id: int,
    message_text: str,
) -> None:
    """Persist a skipped interaction so admin stats stay accurate."""
    interesting = {SKIP_AI_DISABLED, SKIP_BLACKLISTED, SKIP_PAUSED, SKIP_OWNER_ACTIVE, SKIP_TOXIC}
    if skip_reason not in interesting:
        return
    marker_by_reason = {
        SKIP_BLACKLISTED: "[IGNORED: BLACKLISTED]",
        SKIP_PAUSED: "[IGNORED: PAUSED]",
        SKIP_OWNER_ACTIVE: "[IGNORED: OWNER_ACTIVE]",
        SKIP_TOXIC: "[IGNORED: TOXIC]",
    }
    await repo.logs.log_interaction(
        connection_id=connection_id,
        chat_id=chat_id,
        sender_id=sender_id,
        message_text=message_text,
        reply_text=marker_by_reason.get(skip_reason),
    )


def _matches_command(text: str, keyword: str) -> bool:
    """Lightweight detector for stop/resume markers from the owner."""
    if not keyword:
        return False
    return keyword.strip().lower() in (text or "").strip().lower()


async def _handle_owner_hotword(
    repo: BotRepository,
    *,
    chat_id: int,
    message_text: str,
    settings_map: dict[str, str],
) -> bool:
    """React to ``!стоп`` / ``!старт`` style commands the owner types in-chat.

    Returns ``True`` when a hotword was matched, in which case the message
    must not trigger any further processing.
    """
    stop_word = settings_map.get("stop_word", "")
    resume_word = settings_map.get("resume_word", "")

    if _matches_command(message_text, stop_word):
        await repo.chat_state.pause(chat_id, minutes=None)
        logger.info("Owner stop-word detected. Auto-replies paused for chat=%s.", chat_id)
        return True

    if _matches_command(message_text, resume_word):
        await repo.chat_state.resume(chat_id)
        logger.info("Owner resume-word detected. Auto-replies enabled for chat=%s.", chat_id)
        return True

    return False


async def _archive_outgoing_reply(
    repo: BotRepository,
    *,
    sent_message: Message,
    chat_id: int,
    connection_id: str,
    reply_text: str,
) -> None:
    """Best-effort archive of the bot's own reply for future context windows."""
    try:
        await repo.archive.save_message(
            message_id=sent_message.message_id,
            chat_id=chat_id,
            connection_id=connection_id,
            sender_id=settings.ADMIN_ID,
            sender_name=None,
            message_text=reply_text,
        )
    except Exception as archive_error:
        logger.warning(
            "Failed to archive outgoing AI reply for Chat=%s: %s",
            chat_id,
            archive_error,
        )


def _spawn_background_jobs(
    repo: BotRepository,
    *,
    settings_map: dict[str, str],
    chat_id: int,
) -> None:
    """Fire-and-forget AI maintenance for memory, summary and writing style."""

    async def _runner() -> None:
        try:
            await update_auto_memory_if_needed(
                repo,
                settings_map=settings_map,
                chat_id=chat_id,
                owner_id=settings.ADMIN_ID,
            )
        except Exception as exc:
            logger.warning("Auto-memory job error: %s", exc, exc_info=True)
        try:
            await update_summary_if_needed(
                repo,
                settings_map=settings_map,
                chat_id=chat_id,
                owner_id=settings.ADMIN_ID,
            )
        except Exception as exc:
            logger.warning("Summary job error: %s", exc, exc_info=True)
        try:
            await refresh_owner_style_if_needed(
                repo,
                settings_map=settings_map,
                owner_id=settings.ADMIN_ID,
            )
        except Exception as exc:
            logger.warning("Owner-style job error: %s", exc, exc_info=True)

    asyncio.create_task(_runner())


async def _build_and_send_reply(
    *,
    repo: BotRepository,
    message: Message,
    connection_id: str,
    chat_id: int,
    sender_id: int,
    sender_name: str | None,
    message_text: str,
) -> None:
    """Generate an AI reply for the latest message, send it, archive it."""
    settings_map = await repo.settings.all()

    # Re-check skip rules right before replying — paused state, owner activity
    # or fresh blacklist entries may have appeared during the debounce window.
    skip_reason = await skip_reply_reason(
        message_text, sender_id, repo, settings_map, chat_id=chat_id
    )
    if skip_reason:
        await _log_skip(
            repo,
            skip_reason=skip_reason,
            connection_id=connection_id,
            chat_id=chat_id,
            sender_id=sender_id,
            message_text=message_text,
        )
        return

    system_prompt = settings_map.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
    delay = _parse_int(settings_map.get("reply_delay_seconds"), default=0, hi=3600)

    reply_content = await generate_reply(
        repo,
        message_text=message_text,
        system_prompt=system_prompt,
        settings_map=settings_map,
        chat_id=chat_id,
        sender_id=sender_id,
        sender_name=sender_name,
        current_message_id=message.message_id,
    )

    if not reply_content:
        logger.warning("No reply content generated by AI service.")
        return

    if delay > 0:
        logger.info("Delaying reply by %s seconds.", delay)
        await asyncio.sleep(delay)

    try:
        sent = await message.answer(text=reply_content)
        logger.info("Successfully sent business reply to Chat=%s", chat_id)

        await _archive_outgoing_reply(
            repo,
            sent_message=sent,
            chat_id=chat_id,
            connection_id=connection_id,
            reply_text=reply_content,
        )

        await repo.logs.log_interaction(
            connection_id=connection_id,
            chat_id=chat_id,
            sender_id=sender_id,
            message_text=message_text,
            reply_text=reply_content,
        )

        _spawn_background_jobs(repo, settings_map=settings_map, chat_id=chat_id)
    except Exception as e:
        logger.error(
            "Failed to send business reply message. Ensure the bot has can_reply permission. Error: %s",
            e,
            exc_info=True,
        )


async def _debounce_runner(chat_id: int, debounce_seconds: int) -> None:
    """Wait for silence, then reply to the latest pending message in a chat."""
    try:
        await asyncio.sleep(debounce_seconds)
    except asyncio.CancelledError:
        return

    async with _DEBOUNCE_LOCK:
        payload = _DEBOUNCE_PAYLOADS.pop(chat_id, None)
        _DEBOUNCE_TASKS.pop(chat_id, None)

    if payload is None:
        return

    try:
        await _build_and_send_reply(**payload)
    except Exception as exc:
        logger.error(
            "Debounced reply failed for chat=%s: %s",
            chat_id,
            exc,
            exc_info=True,
        )


async def _schedule_debounced_reply(
    *,
    repo: BotRepository,
    message: Message,
    connection_id: str,
    chat_id: int,
    sender_id: int,
    sender_name: str | None,
    message_text: str,
    debounce_seconds: int,
) -> None:
    """Replace any pending timer for ``chat_id`` with a fresh one."""
    payload = {
        "repo": repo,
        "message": message,
        "connection_id": connection_id,
        "chat_id": chat_id,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "message_text": message_text,
    }
    async with _DEBOUNCE_LOCK:
        existing = _DEBOUNCE_TASKS.pop(chat_id, None)
        if existing is not None and not existing.done():
            existing.cancel()
        _DEBOUNCE_PAYLOADS[chat_id] = payload
        _DEBOUNCE_TASKS[chat_id] = asyncio.create_task(
            _debounce_runner(chat_id, debounce_seconds)
        )


@router.business_message()
async def handle_business_message(message: Message, repo: BotRepository, bot: Bot) -> None:
    """Archive a Business message and send an AI reply when allowed."""
    if message.from_user is None:
        logger.debug("Skipping business message without a sender.")
        return

    connection_id = message.business_connection_id
    chat_id = message.chat.id
    sender_id = message.from_user.id
    sender_name = message.from_user.full_name
    message_text = message.text or message.caption or ""

    media_file_path, media_type = await cache_message_media(message, bot)

    logger.info(
        "Received business message: Connection=%s, Chat=%s, Sender=%s, TextLength=%s, MediaType=%s",
        connection_id,
        chat_id,
        sender_id,
        len(message_text),
        media_type,
    )

    await repo.archive.save_message(
        message_id=message.message_id,
        chat_id=chat_id,
        connection_id=connection_id,
        sender_id=sender_id,
        sender_name=sender_name,
        message_text=message_text,
        media_file_path=media_file_path,
        media_type=media_type,
    )

    settings_map = await repo.settings.all()

    # Owner-typed messages never trigger an auto-reply, but we honour stop/resume
    # hotwords so the owner can silence (or wake) the bot in a chat without
    # opening the admin panel.
    if sender_id == settings.ADMIN_ID:
        if message_text:
            await _handle_owner_hotword(
                repo,
                chat_id=chat_id,
                message_text=message_text,
                settings_map=settings_map,
            )
        return

    skip_reason = await skip_reply_reason(
        message_text, sender_id, repo, settings_map, chat_id=chat_id
    )
    if skip_reason:
        await _log_skip(
            repo,
            skip_reason=skip_reason,
            connection_id=connection_id,
            chat_id=chat_id,
            sender_id=sender_id,
            message_text=message_text,
        )
        return

    debounce_seconds = _parse_int(
        settings_map.get("debounce_seconds"), default=8, hi=120
    )

    if debounce_seconds <= 0:
        await _build_and_send_reply(
            repo=repo,
            message=message,
            connection_id=connection_id,
            chat_id=chat_id,
            sender_id=sender_id,
            sender_name=sender_name,
            message_text=message_text,
        )
        return

    await _schedule_debounced_reply(
        repo=repo,
        message=message,
        connection_id=connection_id,
        chat_id=chat_id,
        sender_id=sender_id,
        sender_name=sender_name,
        message_text=message_text,
        debounce_seconds=debounce_seconds,
    )
