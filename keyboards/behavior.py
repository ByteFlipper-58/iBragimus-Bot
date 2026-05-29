from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_behavior_settings_keyboard(context_enabled: bool) -> InlineKeyboardMarkup:
    """Controls for reply delay, ignored words, and conversation context."""
    context_text = "🟢 Контекст диалога: вкл" if context_enabled else "🔴 Контекст диалога: выкл"
    keyboard = [
        [InlineKeyboardButton(text="⏱ Задержка ответа", callback_data="behavior_delay")],
        [InlineKeyboardButton(text="🙅 Игнорируемые слова", callback_data="behavior_ignored")],
        [InlineKeyboardButton(text=context_text, callback_data="behavior_toggle_context")],
        [InlineKeyboardButton(text="🔢 Глубина контекста", callback_data="behavior_context_limit")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_behavior_keyboard() -> InlineKeyboardMarkup:
    """One-button keyboard that returns to behavior settings."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к поведению", callback_data="behavior_settings")]
    ])
