from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_account_qr_keyboard() -> InlineKeyboardMarkup:
    """Controls shown while the QR login session is active."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Новый QR", callback_data="account_login")],
        [InlineKeyboardButton(text="☎️ Войти по телефону", callback_data="account_phone_login")],
        [InlineKeyboardButton(text="🧹 Сбросить сессию", callback_data="account_reset")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu")],
    ])


def get_account_2fa_keyboard() -> InlineKeyboardMarkup:
    """Controls shown while the account 2FA password is awaited."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Начать вход заново", callback_data="account_login")],
        [InlineKeyboardButton(text="☎️ Войти по телефону", callback_data="account_phone_login")],
        [InlineKeyboardButton(text="🧹 Сбросить сессию", callback_data="account_reset")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu")],
    ])


def get_account_phone_keyboard() -> InlineKeyboardMarkup:
    """Controls shown while manual phone login is active."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Войти по QR", callback_data="account_login")],
        [InlineKeyboardButton(text="🧹 Сбросить сессию", callback_data="account_reset")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu")],
    ])


def get_account_status_keyboard(is_authorized: bool) -> InlineKeyboardMarkup:
    """Controls for checking or resetting the connected account."""
    keyboard: list[list[InlineKeyboardButton]] = []
    if not is_authorized:
        keyboard.append([InlineKeyboardButton(text="🔑 Войти по QR", callback_data="account_login")])
        keyboard.append([InlineKeyboardButton(text="☎️ Войти по телефону", callback_data="account_phone_login")])

    keyboard.extend([
        [InlineKeyboardButton(text="🔍 Проверить подключение", callback_data="account_check")],
        [InlineKeyboardButton(text="🧹 Сбросить сессию", callback_data="account_reset")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
