from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

_PROVIDER_LABELS = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
}


def get_ai_settings_keyboard(provider: str) -> InlineKeyboardMarkup:
    """Controls for AI provider, model, and key settings."""
    keyboard = [
        [
            InlineKeyboardButton(
                text=("✅ " if provider == key else "") + label,
                callback_data=f"ai_provider:{key}",
            )
            for key, label in _PROVIDER_LABELS.items()
        ],
        [
            InlineKeyboardButton(text="🧠 Модель", callback_data="ai_edit_model"),
            InlineKeyboardButton(text="🔐 API-ключ", callback_data="ai_edit_key"),
        ],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_ai_settings_keyboard() -> InlineKeyboardMarkup:
    """One-button keyboard that returns to AI settings."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к настройкам ИИ", callback_data="ai_settings")]
    ])


def get_ai_models_keyboard(
    models: list[str],
    selected_model: str,
    page: int = 0,
    per_page: int = 8,
) -> InlineKeyboardMarkup:
    """Controls for selecting a provider model or entering one manually."""
    total = len(models)
    max_page = max(0, (total - 1) // per_page) if total else 0
    page = min(max(page, 0), max_page)
    start = page * per_page
    end = start + per_page

    keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for index, model in enumerate(models[start:end], start=start):
        marker = "✅ " if model == selected_model else ""
        label = model if len(model) <= 28 else f"{model[:25]}..."
        row.append(InlineKeyboardButton(text=f"{marker}{label}", callback_data=f"ai_model:{index}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    if max_page > 0:
        navigation = []
        if page > 0:
            navigation.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"ai_models_page:{page - 1}"))
        navigation.append(InlineKeyboardButton(text=f"{page + 1}/{max_page + 1}", callback_data="ai_models_page:noop"))
        if page < max_page:
            navigation.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"ai_models_page:{page + 1}"))
        keyboard.append(navigation)

    keyboard.extend([
        [InlineKeyboardButton(text="⌨️ Ввести вручную", callback_data="ai_model_manual")],
        [InlineKeyboardButton(text="🔙 Назад к настройкам ИИ", callback_data="ai_settings")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
