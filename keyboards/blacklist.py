from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_back_to_blacklist_keyboard() -> InlineKeyboardMarkup:
    """One-button keyboard that returns to blacklist management."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="manage_blacklist")]
    ])
