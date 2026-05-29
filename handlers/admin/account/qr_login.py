"""QR-based Telegram account login flow."""

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery
from telethon.errors import SessionPasswordNeededError

from handlers.admin.account.errors import format_login_error
from handlers.admin.account.qr import build_qr_png
from handlers.admin.account.status import render_account_status
from handlers.admin.login_session import (
    cancel_login,
    delete_qr_message,
    forget_login_task_if_current,
    get_login_lock,
    remember_login_task,
)
from handlers.admin.states import AdminStates
from handlers.admin.ui import bot_edit_text_safe, edit_text_safe
from keyboards import get_account_2fa_keyboard, get_account_qr_keyboard, get_account_status_keyboard
from telegram_account import get_client

logger = logging.getLogger(__name__)
router = Router(name="admin_account_qr_login")


async def _wait_for_qr_confirmation(
    *,
    admin_id: int,
    bot: Bot,
    state: FSMContext,
    qr_login,
    chat_id: int,
    menu_message_id: int,
    qr_message_id: int,
) -> None:
    """Wait for QR confirmation and finish the Telegram account login flow."""
    current_task = asyncio.current_task()
    try:
        await qr_login.wait()
    except SessionPasswordNeededError:
        await state.set_state(AdminStates.waiting_for_2fa)
        await state.update_data(menu_message_id=menu_message_id)
        await delete_qr_message(bot, chat_id, qr_message_id)
        await bot_edit_text_safe(
            bot,
            chat_id=chat_id,
            message_id=menu_message_id,
            text=(
                "🔐 **Нужен облачный пароль**\n\n"
                "Telegram подтвердил вход по QR, но у аккаунта включена 2FA.\n"
                "Отправь пароль следующим сообщением."
            ),
            reply_markup=get_account_2fa_keyboard(),
            parse_mode="Markdown",
        )
    except asyncio.TimeoutError:
        await state.clear()
        await delete_qr_message(bot, chat_id, qr_message_id)
        await bot_edit_text_safe(
            bot,
            chat_id=chat_id,
            message_id=menu_message_id,
            text="⌛ **Вход по QR истек.**\n\nНажми «Новый QR» и попробуй еще раз.",
            reply_markup=get_account_qr_keyboard(),
            parse_mode="Markdown",
        )
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error("QR login failed: %s", e, exc_info=True)
        await state.clear()
        await delete_qr_message(bot, chat_id, qr_message_id)
        await bot_edit_text_safe(
            bot,
            chat_id=chat_id,
            message_id=menu_message_id,
            text=f"❌ **Не удалось завершить вход по QR**\n\n{format_login_error(e)}",
            reply_markup=get_account_status_keyboard(is_authorized=False),
            parse_mode="Markdown",
        )
    else:
        await state.clear()
        await delete_qr_message(bot, chat_id, qr_message_id)
        await bot_edit_text_safe(
            bot,
            chat_id=chat_id,
            message_id=menu_message_id,
            text=(
                "✅ **Аккаунт Telegram подключен**\n\n"
                "Вход по QR завершен. Аккаунт готов к работе."
            ),
            reply_markup=get_account_status_keyboard(is_authorized=True),
            parse_mode="Markdown",
        )
    finally:
        forget_login_task_if_current(admin_id, current_task)


@router.callback_query(F.data == "account_login")
async def start_account_login(callback: CallbackQuery, state: FSMContext) -> None:
    """Start a fresh QR login flow for the connected Telegram account."""
    lock = get_login_lock(callback.from_user.id)
    if lock.locked():
        await callback.answer("⏳ Вход уже запускается. Подожди пару секунд.", show_alert=True)
        return

    async with lock:
        account_client = get_client()

        data = await state.get_data()
        await delete_qr_message(callback.message.bot, callback.message.chat.id, data.get("qr_message_id"))
        await cancel_login(callback.from_user.id)

        if not account_client.is_connected():
            await account_client.connect()

        if await account_client.is_user_authorized():
            await render_account_status(callback)
            return

        await state.clear()
        await state.set_state(AdminStates.waiting_for_qr_confirm)
        await state.update_data(menu_message_id=callback.message.message_id)

        try:
            qr_login = await account_client.qr_login()
        except Exception as e:
            logger.error("Failed to create QR login token: %s", e, exc_info=True)
            await edit_text_safe(
                callback.message,
                text=f"❌ **Не удалось создать QR-код для входа**\n\n{format_login_error(e)}",
                reply_markup=get_account_status_keyboard(is_authorized=False),
                parse_mode="Markdown",
            )
            await callback.answer("Ошибка создания QR", show_alert=True)
            return

        expires_text = qr_login.expires.strftime("%H:%M:%S UTC")
        await edit_text_safe(
            callback.message,
            text=(
                "🔑 **Вход в аккаунт Telegram**\n\n"
                "Я отправил QR-код отдельной картинкой ниже.\n"
                "Открой Telegram на телефоне: **Настройки → Устройства → Подключить устройство** "
                "и отсканируй картинку.\n"
                "Окно обновится само после подтверждения.\n\n"
                f"QR действует до `{expires_text}`."
            ),
            reply_markup=get_account_qr_keyboard(),
            parse_mode="Markdown",
        )

        qr_message = await callback.message.answer_photo(
            photo=BufferedInputFile(build_qr_png(qr_login.url), filename="telegram_login_qr.png"),
            caption="Сканируй этот QR-код через Telegram: Настройки → Устройства → Подключить устройство.",
        )
        await state.update_data(qr_message_id=qr_message.message_id)
        await callback.answer()

        task = asyncio.create_task(
            _wait_for_qr_confirmation(
                admin_id=callback.from_user.id,
                bot=callback.message.bot,
                state=state,
                qr_login=qr_login,
                chat_id=callback.message.chat.id,
                menu_message_id=callback.message.message_id,
                qr_message_id=qr_message.message_id,
            )
        )
        remember_login_task(callback.from_user.id, task)
