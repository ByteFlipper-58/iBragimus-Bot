"""React to Telegram Business connection updates."""

import logging

from aiogram import Bot, Router
from aiogram.types import BusinessConnection

from database.repository import BotRepository
from services.notifier import send_admin_message

logger = logging.getLogger(__name__)
router = Router(name="business_connections")


def _connected_admin_text(owner_id: int, connection_id: str, can_reply: bool) -> str:
    """Compose the markdown notification sent to the admin on (re)connect."""
    reply_status = (
        "с правом ответа"
        if can_reply
        else "БЕЗ права ответа (пожалуйста, включите права ответа в настройках)"
    )
    return (
        "✅ **iBragimusBot подключен к профилю**\n\n"
        f"👤 Профиль ID: `{owner_id}`\n"
        f"🔑 Connection ID: `{connection_id}`\n"
        f"📊 Статус: `{reply_status}`\n\n"
        "Теперь бот может работать в Business-чатах."
    )


@router.business_connection()
async def handle_business_connection(event: BusinessConnection, repo: BotRepository, bot: Bot) -> None:
    """Persist Telegram Business connection state and notify the admin."""
    connection_id = event.id
    owner_id = event.user.id
    is_enabled = event.is_enabled
    can_reply = event.can_reply

    logger.info(
        "Business Connection Update: ID=%s, Owner=%s, Status=%s, CanReply=%s",
        connection_id,
        owner_id,
        "ПОДКЛЮЧЕН" if is_enabled else "ОТКЛЮЧЕН",
        can_reply,
    )

    await repo.connections.save(
        connection_id=connection_id,
        user_id=owner_id,
        is_enabled=is_enabled,
    )

    if not is_enabled or not bot:
        return

    try:
        await send_admin_message(
            bot,
            _connected_admin_text(owner_id, connection_id, can_reply),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("Failed to notify admin about successful business connection: %s", e, exc_info=True)
