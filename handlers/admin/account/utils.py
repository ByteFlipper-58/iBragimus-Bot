"""Input normalisation and small helpers shared by login flows."""

import logging

from aiogram.types import Message

logger = logging.getLogger(__name__)


def account_name(me) -> str:
    """Format the connected Telegram account display name."""
    name = getattr(me, "first_name", "") or "Без имени"
    if getattr(me, "last_name", None):
        name += f" {me.last_name}"
    return name


def normalize_phone(raw_phone: str) -> str:
    """Normalize admin input into a Telegram phone number candidate."""
    cleaned = "".join(ch for ch in raw_phone.strip() if ch.isdigit() or ch == "+")
    if cleaned.startswith("00"):
        cleaned = f"+{cleaned[2:]}"
    if cleaned and not cleaned.startswith("+"):
        cleaned = f"+{cleaned}"
    return cleaned


def normalize_code(raw_code: str) -> str:
    """Normalize a Telegram login code typed by the admin."""
    return "".join(ch for ch in raw_code.strip() if ch.isalnum())


async def delete_sensitive_message(message: Message, label: str) -> None:
    """Delete an admin message containing phone, code, or password data."""
    try:
        await message.delete()
    except Exception as e:
        logger.debug("Could not delete %s message: %s", label, e)
