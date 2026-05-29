"""Handle the 2FA password step shared by QR and phone login flows."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from telethon.errors import PasswordHashInvalidError

from database.repository import BotRepository
from handlers.admin.account.errors import format_login_error
from handlers.admin.account.utils import delete_sensitive_message
from handlers.admin.context import verify_admin
from handlers.admin.login_session import delete_qr_message
from handlers.admin.states import AdminStates
from handlers.admin.ui import bot_edit_text_safe
from keyboards import get_account_2fa_keyboard, get_account_status_keyboard, get_back_keyboard
from telegram_account import get_client

logger = logging.getLogger(__name__)
router = Router(name="admin_account_twofa")


@router.message(AdminStates.waiting_for_2fa, F.chat.type == "private")
async def finish_account_login_with_2fa(
    message: Message,
    repo: BotRepository,
    state: FSMContext,
) -> None:
    """Finish Telegram account login when the QR or phone flow requires 2FA."""
    if not await verify_admin(message, repo):
        return

    account_client = get_client()
    await delete_sensitive_message(message, "2FA password")

    password = (message.text or "").strip()
    data = await state.get_data()
    menu_message_id = data.get("menu_message_id")
    if not menu_message_id:
        await state.clear()
        await message.answer("❌ Сессия входа истекла. Начните заново.", reply_markup=get_back_keyboard())
        return

    await bot_edit_text_safe(
        message.bot,
        chat_id=message.chat.id,
        message_id=menu_message_id,
        text="⏳ Проверка облачного пароля...",
    )

    try:
        if not account_client.is_connected():
            await account_client.connect()

        await account_client.sign_in(password=password)
        await delete_qr_message(message.bot, message.chat.id, data.get("qr_message_id"))
        await state.clear()
        await bot_edit_text_safe(
            message.bot,
            chat_id=message.chat.id,
            message_id=menu_message_id,
            text=(
                "✅ **Аккаунт Telegram подключен**\n\n"
                "Вход с 2FA завершен. Аккаунт готов к работе."
            ),
            reply_markup=get_account_status_keyboard(is_authorized=True),
            parse_mode="Markdown",
        )
    except PasswordHashInvalidError:
        await bot_edit_text_safe(
            message.bot,
            chat_id=message.chat.id,
            message_id=menu_message_id,
            text="❌ Неверный облачный пароль. Введите пароль еще раз.",
            reply_markup=get_account_2fa_keyboard(),
        )
    except Exception as e:
        logger.error("Failed to sign in with 2FA: %s", e, exc_info=True)
        await bot_edit_text_safe(
            message.bot,
            chat_id=message.chat.id,
            message_id=menu_message_id,
            text=f"❌ **Не удалось войти**\n\n{format_login_error(e)}",
            reply_markup=get_account_2fa_keyboard(),
            parse_mode="Markdown",
        )
