"""Decide whether the bot should auto-reply to an incoming Business message.

Each reason is a short, stable string so handlers can branch on it without
inspecting human-facing copy. The function intentionally returns the *first*
reason it finds, in the same order the previous monolithic handler used.
"""

import logging

from config import settings
from database.repository import BotRepository

logger = logging.getLogger(__name__)

# Reasons known to callers. ``None`` means "do reply".
SKIP_OWNER = "owner"
SKIP_EMPTY = "empty"
SKIP_AI_DISABLED = "ai_disabled"
SKIP_BLACKLISTED = "blacklisted"
SKIP_IGNORED_WORD = "ignored_word"


async def skip_reply_reason(
    message_text: str,
    sender_id: int,
    repo: BotRepository,
    settings_map: dict[str, str],
) -> str | None:
    """Return the reason why the bot should not auto-reply, or ``None`` to reply."""
    if sender_id == settings.ADMIN_ID:
        logger.debug("Skipping message because sender is the business account owner.")
        return SKIP_OWNER

    if not message_text:
        return SKIP_EMPTY

    if settings_map.get("ai_enabled", "1") != "1":
        logger.debug("Skipping message because AI auto-replies are disabled globally.")
        return SKIP_AI_DISABLED

    if await repo.blacklist.contains(sender_id):
        logger.info("Skipping message because sender %s is blacklisted.", sender_id)
        return SKIP_BLACKLISTED

    ignored_words = settings_map.get("ignored_words", "")
    if ignored_words:
        lower_msg = message_text.lower()
        words = [word.strip().lower() for word in ignored_words.split(",") if word.strip()]
        if any(word in lower_msg for word in words):
            logger.info("Skipping message because it contains an ignored word.")
            return SKIP_IGNORED_WORD

    return None
