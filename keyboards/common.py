from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_back_keyboard() -> InlineKeyboardMarkup:
    """One-button keyboard that returns to the admin main menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu")]
    ])
