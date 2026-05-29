"""Notify the admin when archived Business messages are deleted."""

import logging
import os

from aiogram import Bot, Router
from aiogram.types import BusinessMessagesDeleted

from config import settings
from database.repository import BotRepository
from services.catcher.formatters import format_delete_alert
from services.catcher.transcript import generate_bulk_transcript
from services.notifier import send_admin_document, send_admin_media, send_admin_message

logger = logging.getLogger(__name__)
router = Router(name="business_deletions")

BULK_DELETION_THRESHOLD = 3


async def _handle_bulk_deletion(
    *,
    repo: BotRepository,
    bot: Bot,
    chat_id: int,
    message_ids: list[int],
) -> bool:
    """Send a transcript when many messages are deleted at once.

    Returns ``True`` when the deletion was treated as a bulk event, so the
    caller can skip the per-message branch.
    """
    if len(message_ids) <= BULK_DELETION_THRESHOLD:
        return False

    logger.info("Bulk deletion detected in chat %s. Recovering messages for transcript backup.", chat_id)

    archived = await repo.archive.get_messages(message_ids, chat_id)

    recovered_entries: list[dict] = []
    sender_id: int | None = None
    sender_name = "Неизвестный"

    for message_id in message_ids:
        original = archived.get(message_id)
        if not original:
            continue
        recovered_entries.append(original)
        sender_id = original["sender_id"]
        sender_name = original["sender_name"] or "Неизвестный"
        await repo.archive.log_deletion(message_id, chat_id, original["message_text"])

    if not recovered_entries or sender_id == settings.ADMIN_ID:
        return True

    file_path, alert_text = generate_bulk_transcript(
        chat_id=chat_id,
        message_ids=message_ids,
        recovered_entries=recovered_entries,
        sender_id=sender_id,
        sender_name=sender_name,
    )

    try:
        await send_admin_document(bot, file_path, alert_text, cleanup=True)
        logger.info("Sent bulk deletion transcript backup to admin for chat %s", chat_id)
    except Exception as e:
        logger.error("Failed to send bulk deletion document: %s", e, exc_info=True)
        if os.path.exists(file_path):
            os.remove(file_path)

    return True


async def _handle_single_deletion(
    repo: BotRepository,
    bot: Bot,
    *,
    chat_id: int,
    message_id: int,
    archived: dict[int, dict],
) -> None:
    """Process a single deleted message: log it and notify the admin."""
    original = archived.get(message_id)
    if not original:
        logger.debug("Deleted message %s was not found in database archive.", message_id)
        return

    sender_id = original["sender_id"]
    message_text = original["message_text"]

    await repo.archive.log_deletion(message_id, chat_id, message_text)

    if sender_id == settings.ADMIN_ID:
        return

    try:
        alert_text, media_file_path, media_type = format_delete_alert(original)

        if media_file_path and os.path.exists(media_file_path):
            await send_admin_media(bot, media_file_path, media_type, alert_text)
        else:
            await send_admin_message(bot, alert_text)
        logger.info("Sent delete alert for message %s (media: %s)", message_id, media_type is not None)
    except Exception as e:
        logger.error("Failed to send deletion alert to admin: %s", e, exc_info=True)


@router.deleted_business_messages()
async def handle_deleted_business_messages(event: BusinessMessagesDeleted, repo: BotRepository, bot: Bot) -> None:
    """Notify the admin when archived Business messages are deleted."""
    chat_id = event.chat.id
    message_ids = event.message_ids

    logger.info("Business messages deleted in chat %s: IDs=%s", chat_id, message_ids)

    if not bot:
        return

    if await _handle_bulk_deletion(repo=repo, bot=bot, chat_id=chat_id, message_ids=message_ids):
        return

    archived = await repo.archive.get_messages(message_ids, chat_id)
    for message_id in message_ids:
        await _handle_single_deletion(
            repo,
            bot,
            chat_id=chat_id,
            message_id=message_id,
            archived=archived,
        )
