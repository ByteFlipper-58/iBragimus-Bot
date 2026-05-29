"""Helpers for sending notifications to the bot administrator.

Centralises the ``bot.send_message(chat_id=settings.ADMIN_ID, ...)`` pattern
that was previously duplicated in several Business handlers. The module also
hides the per-media-type dispatching used when forwarding cached deleted media
back to the admin chat.
"""

import logging
import os

from aiogram import Bot
from aiogram.types import FSInputFile

from config import settings

logger = logging.getLogger(__name__)


async def send_admin_message(bot: Bot, text: str, parse_mode: str = "HTML") -> None:
    """Send a plain text message to the admin chat."""
    await bot.send_message(chat_id=settings.ADMIN_ID, text=text, parse_mode=parse_mode)


async def send_admin_document(
    bot: Bot,
    file_path: str,
    caption: str,
    *,
    parse_mode: str = "HTML",
    cleanup: bool = False,
) -> None:
    """Send a local document to the admin chat, optionally deleting it after."""
    try:
        await bot.send_document(
            chat_id=settings.ADMIN_ID,
            document=FSInputFile(file_path),
            caption=caption,
            parse_mode=parse_mode,
        )
    finally:
        if cleanup and os.path.exists(file_path):
            os.remove(file_path)


_MEDIA_SENDERS = {
    "photo": ("send_photo", "photo"),
    "video": ("send_video", "video"),
    "voice": ("send_voice", "voice"),
    "document": ("send_document", "document"),
    "audio": ("send_audio", "audio"),
    "animation": ("send_animation", "animation"),
    # Stickers cannot carry captions in Telegram, so re-send them as documents.
    "sticker": ("send_document", "document"),
}


async def send_admin_media(
    bot: Bot,
    media_file_path: str,
    media_type: str | None,
    caption: str,
    *,
    parse_mode: str = "HTML",
) -> None:
    """Send a cached media file to the admin chat using the matching API method.

    Falls back to a plain text message when ``media_type`` is unknown.
    """
    method_info = _MEDIA_SENDERS.get(media_type or "")
    if method_info is None:
        await send_admin_message(bot, caption, parse_mode=parse_mode)
        return

    method_name, kw = method_info
    media_file = FSInputFile(media_file_path)
    send = getattr(bot, method_name)
    await send(
        chat_id=settings.ADMIN_ID,
        **{kw: media_file},
        caption=caption,
        parse_mode=parse_mode,
    )
