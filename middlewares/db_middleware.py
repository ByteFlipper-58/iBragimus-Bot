import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database.repository import BotRepository

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """Injects BotRepository into aiogram handler context."""

    def __init__(self, repository: BotRepository):
        self.repository = repository
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["repo"] = self.repository
        return await handler(event, data)
