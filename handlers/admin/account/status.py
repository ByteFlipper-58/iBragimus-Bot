"""Render and refresh the connected Telegram account status."""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from handlers.admin.account.errors import format_login_error
from handlers.admin.account.utils import account_name
from handlers.admin.ui import edit_text_safe
from keyboards import get_account_status_keyboard
from telegram_account import get_client

logger = logging.getLogger(__name__)
router = Router(name="admin_account_status")


def _unauthorized_text() -> str:
    return (
        "🟡 **Аккаунт Telegram не авторизован**\n\n"
        "🔌 **Соединение:** `подключено`\n"
        "🔐 **Авторизация:** `нет`\n\n"
        "Можно подключить аккаунт по QR или вручную через номер телефона."
    )


def _authorized_text(me) -> str:
    phone = getattr(me, "phone", None)
    phone_text = f"+{phone}" if phone else "Скрыт"
    return (
        "🟢 **Аккаунт Telegram подключен**\n\n"
        "🔌 **Соединение:** `подключено`\n"
        "🔐 **Авторизация:** `да`\n"
        f"👤 **Аккаунт:** {account_name(me)}\n"
        f"📞 **Телефон:** `{phone_text}`\n"
        f"🆔 **ID:** `{me.id}`\n\n"
        "Одноразовые фото и видео автоматически сохраняются и отправляются в **Saved Messages**."
    )


def _pending_text() -> str:
    return (
        "🟠 **Аккаунт Telegram требует проверки**\n\n"
        "Клиент подключен и авторизован, но Telegram не вернул данные профиля.\n"
        "Нажми «Проверить подключение» ещё раз."
    )


async def render_account_status(callback: CallbackQuery, *, checked: bool = False) -> None:
    """Connect to Telegram, inspect account auth state, and render the admin status screen."""
    account_client = get_client()
    try:
        if not account_client.is_connected():
            await account_client.connect()

        if not await account_client.is_user_authorized():
            await edit_text_safe(
                callback.message,
                text=_unauthorized_text(),
                reply_markup=get_account_status_keyboard(is_authorized=False),
                parse_mode="Markdown",
            )
            await callback.answer("Проверено" if checked else None)
            return

        me = await account_client.get_me()
        if not me:
            await edit_text_safe(
                callback.message,
                text=_pending_text(),
                reply_markup=get_account_status_keyboard(is_authorized=False),
                parse_mode="Markdown",
            )
            await callback.answer("Не удалось получить профиль", show_alert=True)
            return

        await edit_text_safe(
            callback.message,
            text=_authorized_text(me),
            reply_markup=get_account_status_keyboard(is_authorized=True),
            parse_mode="Markdown",
        )
        await callback.answer("Проверено" if checked else None)
    except Exception as e:
        logger.error("Failed to check Telegram account status: %s", e, exc_info=True)
        await edit_text_safe(
            callback.message,
            text=f"❌ **Не удалось проверить аккаунт Telegram**\n\n{format_login_error(e)}",
            reply_markup=get_account_status_keyboard(is_authorized=False),
            parse_mode="Markdown",
        )
        await callback.answer("Ошибка проверки аккаунта", show_alert=True)


@router.callback_query(F.data == "account_status")
async def show_account_status(callback: CallbackQuery) -> None:
    """Show the currently connected Telegram account status."""
    await render_account_status(callback)


@router.callback_query(F.data == "account_check")
async def check_account_connection(callback: CallbackQuery) -> None:
    """Force a fresh Telegram account status check."""
    await render_account_status(callback, checked=True)
