"""Helpers shared by admin handlers: auth, AI status, account state."""

import asyncio
import logging

from aiogram.types import Message

from config import settings
from database.repository import BotRepository
from telegram_account import get_existing_client

logger = logging.getLogger(__name__)


async def get_account_status() -> str:
    """Return the connected account state used by the admin keyboard."""
    account_client = get_existing_client()
    if not account_client:
        return "disabled"
    if not account_client.is_connected():
        return "disconnected"
    try:
        is_authorized = await asyncio.wait_for(account_client.is_user_authorized(), timeout=5)
    except Exception as e:
        logger.warning("Could not determine Telegram account authorization state: %s", e)
        return "disconnected"
    return "authorized" if is_authorized else "unauthorized"


async def get_ai_enabled(repo: BotRepository) -> bool:
    """Return whether AI auto-replies are enabled."""
    return await repo.settings.get("ai_enabled", "1") == "1"


async def verify_admin(message: Message, _repo: BotRepository) -> bool:
    """Allow only the configured administrator to use private bot controls."""
    if message.from_user.id != settings.ADMIN_ID:
        await message.answer("❌ Доступ только для администратора iBragimusBot.")
        return False
    return True
