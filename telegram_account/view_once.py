"""View-once media interceptor for the connected Telethon client."""

import logging
import time

from telethon import TelegramClient, events

from services.catcher.paths import view_once_dir
from telegram_account.media import (
    format_ttl,
    is_view_once_media,
    media_download_target,
    sender_display_name,
)

logger = logging.getLogger("telegram_account")

_MAX_TRACKED_VIEW_ONCE_IDS = 2048
_processed_view_once_ids: set[tuple[int, int]] = set()


def reset_processed_cache() -> None:
    """Drop the in-memory deduplication cache (e.g. on session reset)."""
    _processed_view_once_ids.clear()


def _remember_processed(message_key: tuple[int, int]) -> None:
    """Record a processed message key, evicting on overflow."""
    if len(_processed_view_once_ids) >= _MAX_TRACKED_VIEW_ONCE_IDS:
        _processed_view_once_ids.clear()
    _processed_view_once_ids.add(message_key)


def register_view_once_handler(account_client: TelegramClient) -> None:
    """Register the view-once media interceptor on a Telethon client."""

    @account_client.on(events.NewMessage(incoming=True))
    async def on_new_message(event) -> None:
        if not event.media:
            return

        ttl = getattr(event.media, "ttl_seconds", None)
        if not is_view_once_media(event.media):
            return

        message_key = (event.chat_id or 0, event.id)
        if message_key in _processed_view_once_ids:
            logger.debug("Skipping duplicate view-once media event: %s", message_key)
            return
        _remember_processed(message_key)

        sender = await event.get_sender()
        sender_info = sender_display_name(sender)
        download_target, media_kind, extension = media_download_target(event.media)
        timestamp = int(time.time())

        logger.info(
            "Detected view-once %s from %s. Timer: %s.",
            media_kind,
            sender_info,
            format_ttl(ttl),
        )

        cache_dir = view_once_dir(event.sender_id)
        chat_part = event.chat_id if event.chat_id is not None else "unknown"
        file_path = cache_dir / f"{timestamp}_{chat_part}_{event.id}{extension}"

        try:
            downloaded_path = await account_client.download_media(
                download_target,
                file=str(file_path),
                thumb=None,
            )
            if not downloaded_path:
                logger.error("Telegram returned no path after downloading view-once media.")
                return

            from pathlib import Path

            downloaded_file = Path(downloaded_path)
            if not downloaded_file.exists():
                logger.error("Download completed but cached file was not found: %s", downloaded_file)
                return

            logger.info("Successfully cached view-once media: %s", downloaded_file)

            caption = (
                "**Одноразовое медиа сохранено**\n\n"
                f"Отправитель: {sender_info}\n"
                f"ID: `{event.sender_id}`\n"
                f"Тип: `{media_kind}`\n"
                f"Удаление: {format_ttl(ttl)}\n"
                f"Файл: `{downloaded_file}`"
            )

            try:
                await account_client.send_file(
                    entity="me",
                    file=str(downloaded_file),
                    caption=caption,
                    force_document=(media_kind not in {"photo", "image", "video"}),
                    supports_streaming=(media_kind == "video"),
                )
                logger.info("Sent saved copy to Saved Messages.")
            except Exception as e:
                logger.error(
                    "Saved local copy, but failed to send it to Saved Messages: %s",
                    e,
                    exc_info=True,
                )
        except Exception as e:
            logger.error("Failed to intercept and download view-once media: %s", e, exc_info=True)
