"""Map Telethon login errors into short admin-facing explanations."""

from telethon.errors import (
    AuthKeyDuplicatedError,
    AuthKeyInvalidError,
    AuthKeyPermEmptyError,
    AuthKeyUnregisteredError,
    FloodWaitError,
    PasswordHashInvalidError,
    PhoneCodeEmptyError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberBannedError,
    PhoneNumberInvalidError,
)

AUTH_KEY_ERRORS = (
    AuthKeyDuplicatedError,
    AuthKeyInvalidError,
    AuthKeyPermEmptyError,
    AuthKeyUnregisteredError,
)


def format_login_error(error: Exception) -> str:
    """Return a concise admin-facing explanation for a Telethon login error."""
    if isinstance(error, FloodWaitError):
        return f"Telegram временно ограничил вход. Подожди `{error.seconds}` сек. и попробуй снова."
    if isinstance(error, AUTH_KEY_ERRORS):
        return "Локальная сессия Telegram недействительна. Нажми «Сбросить сессию» и войди заново."
    if isinstance(error, PasswordHashInvalidError):
        return "Неверный облачный пароль Telegram. Введи пароль ещё раз."
    if isinstance(error, PhoneNumberInvalidError):
        return "Telegram не принял номер. Введи номер в международном формате, например `+79991234567`."
    if isinstance(error, PhoneNumberBannedError):
        return "Этот номер заблокирован Telegram и не может быть использован для входа."
    if isinstance(error, PhoneCodeExpiredError):
        return "Код Telegram устарел. Запусти вход по телефону заново и запроси новый код."
    if isinstance(error, (PhoneCodeEmptyError, PhoneCodeInvalidError)):
        return "Код Telegram неверный. Проверь код и отправь его ещё раз."
    return f"`{type(error).__name__}: {error}`"
