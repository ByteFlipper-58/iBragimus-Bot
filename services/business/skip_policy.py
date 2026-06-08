"""Decide whether the bot should auto-reply to an incoming Business message.

Each reason is a short, stable string so handlers can branch on it without
inspecting human-facing copy. The function intentionally returns the *first*
reason it finds, in the same order the previous monolithic handler used.
"""

import logging
from datetime import datetime, timedelta

from config import settings
from database.repository import BotRepository

logger = logging.getLogger(__name__)

# Reasons known to callers. ``None`` means "do reply".
SKIP_OWNER = "owner"
SKIP_EMPTY = "empty"
SKIP_AI_DISABLED = "ai_disabled"
SKIP_BLACKLISTED = "blacklisted"
SKIP_IGNORED_WORD = "ignored_word"
SKIP_PAUSED = "paused"
SKIP_OWNER_ACTIVE = "owner_active"
SKIP_TOXIC = "toxic"


_DEFAULT_TOXIC_KEYWORDS: tuple[str, ...] = (
    "иди нахуй",
    "пошёл нахуй",
    "пошел нахуй",
    "fuck you",
    "сдохни",
    "убью",
    "ненавижу тебя",
    "тварь",
    "сука",
    "шлюха",
    "пидор",
    "чмо",
    "kill yourself",
    "kys",
)


def _toxic_keywords(settings_map: dict[str, str]) -> list[str]:
    """Return the configured toxicity keyword list.

    Admin-provided keywords take priority. When the field is empty we fall
    back to a small default set so the feature still does something useful
    out of the box.
    """
    raw = (settings_map.get("toxicity_keywords") or "").strip()
    if not raw:
        return list(_DEFAULT_TOXIC_KEYWORDS)
    return [
        word.strip().lower()
        for word in raw.split(",")
        if word.strip()
    ]


def _looks_toxic(message_text: str, settings_map: dict[str, str]) -> bool:
    if settings_map.get("toxicity_filter_enabled", "1") != "1":
        return False
    keywords = _toxic_keywords(settings_map)
    if not keywords:
        return False
    lowered = message_text.lower()
    return any(word in lowered for word in keywords)


async def _owner_active_recently(
    repo: BotRepository,
    chat_id: int,
    settings_map: dict[str, str],
) -> bool:
    """Return ``True`` if the owner himself wrote in the chat recently.

    The owner's outgoing messages are archived alongside incoming ones, so
    we can check whether they typed within the configured pause window. AI
    replies authored by the bot are filtered out by ignoring messages that
    triggered a logged interaction is not necessary here — the owner's own
    messages always come from the connected userbot session and predate any
    bot-authored archive entry by definition.
    """
    try:
        minutes = max(0, int(settings_map.get("owner_pause_minutes", "15")))
    except (ValueError, TypeError):
        minutes = 15
    if minutes <= 0:
        return False

    last_owner = await repo.archive.get_last_owner_message(chat_id, settings.ADMIN_ID)
    if not last_owner:
        return False

    raw_ts = last_owner.get("created_at")
    if not raw_ts:
        return False

    if isinstance(raw_ts, datetime):
        ts = raw_ts.replace(tzinfo=None) if raw_ts.tzinfo else raw_ts
    else:
        try:
            ts = datetime.strptime(str(raw_ts), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return False

    return ts > (datetime.utcnow() - timedelta(minutes=minutes))


async def skip_reply_reason(
    message_text: str,
    sender_id: int,
    repo: BotRepository,
    settings_map: dict[str, str],
    *,
    chat_id: int | None = None,
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

    if chat_id is not None and await repo.chat_state.is_paused(chat_id):
        logger.info("Skipping message because chat %s is paused.", chat_id)
        return SKIP_PAUSED

    if chat_id is not None and await _owner_active_recently(repo, chat_id, settings_map):
        logger.info("Skipping message because the owner is active in chat %s.", chat_id)
        return SKIP_OWNER_ACTIVE

    if _looks_toxic(message_text, settings_map):
        logger.info("Skipping message because it looks toxic.")
        return SKIP_TOXIC

    return None
