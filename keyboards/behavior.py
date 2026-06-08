from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_behavior_settings_keyboard(
    context_enabled: bool,
    toxicity_enabled: bool = True,
) -> InlineKeyboardMarkup:
    """Controls for reply delay, ignored words, and conversation context."""
    context_text = "🟢 Контекст диалога: вкл" if context_enabled else "🔴 Контекст диалога: выкл"
    toxicity_text = "🛡 Фильтр токсичности: вкл" if toxicity_enabled else "🛡 Фильтр токсичности: выкл"
    keyboard = [
        [InlineKeyboardButton(text="⏱ Задержка ответа", callback_data="behavior_delay")],
        [InlineKeyboardButton(text="⏳ Дебаунс серии", callback_data="behavior_debounce")],
        [InlineKeyboardButton(text="🤐 Пауза при активности владельца", callback_data="behavior_owner_pause")],
        [InlineKeyboardButton(text="🛑 Стоп-слово", callback_data="behavior_stop_word")],
        [InlineKeyboardButton(text="▶️ Старт-слово", callback_data="behavior_resume_word")],
        [InlineKeyboardButton(text=toxicity_text, callback_data="behavior_toggle_toxicity")],
        [InlineKeyboardButton(text="📜 Слова токсичности", callback_data="behavior_toxicity_words")],
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
