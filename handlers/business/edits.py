"""Track edited Business messages and notify the admin about changes."""

import logging

from aiogram import Bot, F, Router
from aiogram.types import Message

from config import settings
from database.repository import BotRepository
from services.catcher.formatters import format_edit_timeline
from services.notifier import send_admin_message

logger = logging.getLogger(__name__)
router = Router(name="business_edits")


@router.edited_business_message(F.text)
async def handle_edited_business_message(message: Message, repo: BotRepository, bot: Bot) -> None:
    """Update the message archive and notify the admin about text edits."""
    if message.from_user is None:
        logger.debug("Skipping edited business message without a sender.")
        return

    connection_id = message.business_connection_id
    chat_id = message.chat.id
    sender_id = message.from_user.id
    new_text = message.text
    message_id = message.message_id

    original = await repo.archive.get_message(message_id, chat_id)
    if not original:
        logger.debug("Edited message %s not found in DB archive. Saving new text.", message_id)
        await repo.archive.save_message(
            message_id=message_id,
            chat_id=chat_id,
            connection_id=connection_id,
            sender_id=sender_id,
            sender_name=message.from_user.full_name,
            message_text=new_text,
        )
        return

    old_text = original["message_text"]
    if old_text == new_text:
        return

    await repo.archive.log_edit(message_id, chat_id, old_text, new_text)
    await repo.archive.save_message(
        message_id=message_id,
        chat_id=chat_id,
        connection_id=connection_id,
        sender_id=sender_id,
        sender_name=original["sender_name"],
        message_text=new_text,
    )

    if sender_id == settings.ADMIN_ID or not bot:
        return

    try:
        history = await repo.archive.get_edit_history(message_id, chat_id)
        alert_text = format_edit_timeline(
            sender_id=sender_id,
            sender_name=original["sender_name"],
            old_text=old_text,
            new_text=new_text,
            history=history,
        )

        await send_admin_message(bot, alert_text)
        logger.info("Sent edit history alert to admin for message %s", message_id)
    except Exception as e:
        logger.error("Failed to send edit alert to admin: %s", e, exc_info=True)
