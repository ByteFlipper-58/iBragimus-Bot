"""Download Telegram media into the local media cache."""

import logging

from aiogram import Bot

from services.catcher.paths import chat_cache_dir

logger = logging.getLogger(__name__)


async def download_media_file(
    bot: Bot,
    file_id: str,
    chat_id: int,
    message_id: int,
    m_type: str,
    ext: str,
) -> str | None:
    """Download a Telegram file and persist it to ``media_cache/<chat>/``."""
    try:
        file_path = chat_cache_dir(chat_id) / f"{message_id}_{m_type}.{ext}"

        file_info = await bot.get_file(file_id)
        if not file_info.file_path:
            return None

        await bot.download_file(file_info.file_path, str(file_path))
        logger.info(
            "Successfully downloaded and cached %s for message %s in chat %s",
            m_type,
            message_id,
            chat_id,
        )
        return str(file_path)
    except Exception as e:
        logger.error(
            "Failed to download and cache %s file for message %s: %s",
            m_type,
            message_id,
            e,
            exc_info=True,
        )
        return None
