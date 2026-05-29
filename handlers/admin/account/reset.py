"""Drop the local Telegram session and recreate the Telethon client."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from handlers.admin.account.errors import format_login_error
from handlers.admin.login_session import cancel_login, delete_qr_message, get_login_lock
from handlers.admin.ui import edit_text_safe
from keyboards import get_account_status_keyboard
from telegram_account import reset_client_session

logger = logging.getLogger(__name__)
router = Router(name="admin_account_reset")


@router.callback_query(F.data == "account_reset")
async def reset_account_connection(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel login, delete the local Telegram account session, and create a clean client."""
    lock = get_login_lock(callback.from_user.id)
    if lock.locked():
        await callback.answer("⏳ Действие со входом уже выполняется.", show_alert=True)
        return

    async with lock:
        data = await state.get_data()
        await delete_qr_message(callback.message.bot, callback.message.chat.id, data.get("qr_message_id"))
        await cancel_login(callback.from_user.id)
        await state.clear()

        try:
            reset_client = await reset_client_session()
            await reset_client.connect()
            await edit_text_safe(
                callback.message,
                text=(
                    "🧹 **Сессия аккаунта сброшена**\n\n"
                    "Локальный файл сессии удалён, клиент создан заново.\n"
                    "Теперь можно подключить аккаунт через новый QR."
                ),
                reply_markup=get_account_status_keyboard(is_authorized=False),
                parse_mode="Markdown",
            )
            await callback.answer("Сессия сброшена")
        except Exception as e:
            logger.error("Failed to reset Telegram account session: %s", e, exc_info=True)
            await edit_text_safe(
                callback.message,
                text=f"❌ **Не удалось сбросить сессию**\n\n{format_login_error(e)}",
                reply_markup=get_account_status_keyboard(is_authorized=False),
                parse_mode="Markdown",
            )
            await callback.answer("Ошибка сброса сессии", show_alert=True)
