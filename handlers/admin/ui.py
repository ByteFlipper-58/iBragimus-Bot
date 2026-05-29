from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message


def is_message_not_modified(error: TelegramBadRequest) -> bool:
    """Return whether Telegram rejected an edit because the content is unchanged."""
    return "message is not modified" in str(error).lower()


async def edit_text_safe(message: Message, **kwargs) -> None:
    """Edit an aiogram message while ignoring duplicate-content edits."""
    try:
        await message.edit_text(**kwargs)
    except TelegramBadRequest as e:
        if not is_message_not_modified(e):
            raise


async def bot_edit_text_safe(bot, **kwargs) -> None:
    """Edit a message through Bot API while ignoring duplicate-content edits."""
    try:
        await bot.edit_message_text(**kwargs)
    except TelegramBadRequest as e:
        if not is_message_not_modified(e):
            raise
