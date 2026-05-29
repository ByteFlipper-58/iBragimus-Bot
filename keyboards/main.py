from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_keyboard(ai_enabled: bool, account_status: str) -> InlineKeyboardMarkup:
    """Build the admin panel keyboard for the current bot/account state."""
    ai_status_text = "🟢 Автоответы: вкл" if ai_enabled else "🔴 Автоответы: выкл"

    keyboard = [
        [InlineKeyboardButton(text=ai_status_text, callback_data="toggle_ai")]
    ]

    if account_status == "unauthorized":
        keyboard.append([
            InlineKeyboardButton(text="🔑 Войти в аккаунт Telegram", callback_data="account_login")
        ])
    elif account_status == "authorized":
        keyboard.append([
            InlineKeyboardButton(text="🟢 Аккаунт: подключен", callback_data="account_status")
        ])
    elif account_status == "disabled":
        keyboard.append([
            InlineKeyboardButton(text="⚠️ Аккаунт: не настроен", callback_data="how_to_connect")
        ])
    elif account_status == "disconnected":
        keyboard.append([
            InlineKeyboardButton(text="🔌 Аккаунт: переподключить", callback_data="account_login")
        ])

    keyboard.extend([
        [
            InlineKeyboardButton(text="✏️ Изменить промпт", callback_data="edit_prompt"),
            InlineKeyboardButton(text="📋 Текущий промпт", callback_data="view_prompt"),
        ],
        [InlineKeyboardButton(text="🤖 Настройки ИИ", callback_data="ai_settings")],
        [InlineKeyboardButton(text="⚙️ Поведение автоответов", callback_data="behavior_settings")],
        [
            InlineKeyboardButton(text="🚫 Черный список", callback_data="manage_blacklist"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="view_stats"),
        ],
        [InlineKeyboardButton(text="ℹ️ Как подключить аккаунт", callback_data="how_to_connect")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
