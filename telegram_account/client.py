"""Telethon client lifecycle: initialise, share, and reset."""

import logging

from telethon import TelegramClient

from config import settings
from telegram_account.session import SESSION_NAME, session_paths
from telegram_account.view_once import register_view_once_handler, reset_processed_cache

logger = logging.getLogger("telegram_account")

_client: TelegramClient | None = None


def init_client() -> TelegramClient:
    """Initialize the Telegram account client for view-once media interception."""
    global _client
    if _client is not None:
        return _client

    logger.info("Initializing Telegram account session...")
    _client = TelegramClient(SESSION_NAME, settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
    register_view_once_handler(_client)
    return _client


def get_client() -> TelegramClient:
    """Return the active Telegram account client, creating it on first use."""
    return init_client()


def get_existing_client() -> TelegramClient | None:
    """Return the current Telegram account client without creating a new one."""
    return _client


async def reset_client_session() -> TelegramClient:
    """Disconnect the current client, drop its session files, and create a clean client."""
    global _client

    if _client is not None:
        if _client.is_connected():
            await _client.disconnect()
        _client.session.delete()
        _client = None

    reset_processed_cache()

    for path in session_paths():
        if path.exists():
            path.unlink()
            logger.info("Deleted Telegram account session file: %s", path)

    return init_client()
