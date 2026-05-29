"""Manual Telegram account login by phone number and Telegram code."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from telethon.errors import (
    PhoneCodeEmptyError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)

from database.repository import BotRepository
from handlers.admin.account.errors import format_login_error
from handlers.admin.account.status import render_account_status
from handlers.admin.account.utils import delete_sensitive_message, normalize_code, normalize_phone
from handlers.admin.context import verify_admin
from handlers.admin.login_session import cancel_login, delete_qr_message, get_login_lock
from handlers.admin.states import AdminStates
from handlers.admin.ui import bot_edit_text_safe, edit_text_safe
from keyboards import (
    get_account_2fa_keyboard,
    get_account_phone_keyboard,
    get_account_status_keyboard,
    get_back_keyboard,
)
from telegram_account import get_client

logger = logging.getLogger(__name__)
router = Router(name="admin_account_phone_login")

MIN_PHONE_LENGTH = 8


@router.callback_query(F.data == "account_phone_login")
async def start_phone_login(callback: CallbackQuery, state: FSMContext) -> None:
    """Start manual Telegram account login by phone number and login code."""
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
        await state.set_state(AdminStates.waiting_for_phone)
        await state.update_data(menu_message_id=callback.message.message_id)
        await edit_text_safe(
            callback.message,
            text=(
                "☎️ **Вход по телефону**\n\n"
                "Отправь номер аккаунта Telegram следующим сообщением.\n"
                "Формат: `+79991234567`.\n\n"
                "После этого Telegram пришлёт код в приложение или SMS."
            ),
            reply_markup=get_account_phone_keyboard(),
            parse_mode="Markdown",
        )
        await callback.answer()


@router.message(AdminStates.waiting_for_phone, F.chat.type == "private")
async def request_phone_login_code(message: Message, repo: BotRepository, state: FSMContext) -> None:
    """Send a Telegram login code to the phone number provided by the admin."""
    if not await verify_admin(message, repo):
        return

    await delete_sensitive_message(message, "phone login")

    phone = normalize_phone(message.text or "")
    data = await state.get_data()
    menu_message_id = data.get("menu_message_id")
    if not menu_message_id:
        await state.clear()
        await message.answer("❌ Сессия входа истекла. Начните заново.", reply_markup=get_back_keyboard())
        return

    if len(phone) < MIN_PHONE_LENGTH:
        await bot_edit_text_safe(
            message.bot,
            chat_id=message.chat.id,
            message_id=menu_message_id,
            text=(
                "❌ **Номер слишком короткий**\n\n"
                "Отправь номер в международном формате, например `+79991234567`."
            ),
            reply_markup=get_account_phone_keyboard(),
            parse_mode="Markdown",
        )
        return

    account_client = get_client()
    try:
        if not account_client.is_connected():
            await account_client.connect()

        sent_code = await account_client.send_code_request(phone)
        await state.set_state(AdminStates.waiting_for_code)
        await state.update_data(phone=phone, phone_code_hash=sent_code.phone_code_hash)
        await bot_edit_text_safe(
            message.bot,
            chat_id=message.chat.id,
            message_id=menu_message_id,
            text=(
                "📩 **Код отправлен**\n\n"
                f"Номер: `{phone}`\n"
                "Отправь код Telegram следующим сообщением.\n\n"
                "Если код не пришёл, нажми «Войти по телефону» и запроси его заново."
            ),
            reply_markup=get_account_phone_keyboard(),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("Failed to send Telegram login code: %s", e, exc_info=True)
        await bot_edit_text_safe(
            message.bot,
            chat_id=message.chat.id,
            message_id=menu_message_id,
            text=f"❌ **Не удалось отправить код Telegram**\n\n{format_login_error(e)}",
            reply_markup=get_account_phone_keyboard(),
            parse_mode="Markdown",
        )


@router.message(AdminStates.waiting_for_code, F.chat.type == "private")
async def finish_phone_login_with_code(message: Message, repo: BotRepository, state: FSMContext) -> None:
    """Finish manual Telegram account login with the code sent by Telegram."""
    if not await verify_admin(message, repo):
        return

    await delete_sensitive_message(message, "phone code")

    code = normalize_code(message.text or "")
    data = await state.get_data()
    menu_message_id = data.get("menu_message_id")
    phone = data.get("phone")
    phone_code_hash = data.get("phone_code_hash")
    if not menu_message_id or not phone or not phone_code_hash:
        await state.clear()
        await message.answer("❌ Сессия входа истекла. Начните заново.", reply_markup=get_back_keyboard())
        return

    if not code:
        await bot_edit_text_safe(
            message.bot,
            chat_id=message.chat.id,
            message_id=menu_message_id,
            text="❌ Код пустой. Отправь код Telegram следующим сообщением.",
            reply_markup=get_account_phone_keyboard(),
        )
        return

    account_client = get_client()
    try:
        if not account_client.is_connected():
            await account_client.connect()

        await account_client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        await state.clear()
        await bot_edit_text_safe(
            message.bot,
            chat_id=message.chat.id,
            message_id=menu_message_id,
            text=(
                "✅ **Аккаунт Telegram подключен**\n\n"
                "Вход по телефону завершён. Аккаунт готов к работе."
            ),
            reply_markup=get_account_status_keyboard(is_authorized=True),
            parse_mode="Markdown",
        )
    except SessionPasswordNeededError:
        await state.set_state(AdminStates.waiting_for_2fa)
        await state.update_data(menu_message_id=menu_message_id)
        await bot_edit_text_safe(
            message.bot,
            chat_id=message.chat.id,
            message_id=menu_message_id,
            text=(
                "🔐 **Код принят, нужен облачный пароль**\n\n"
                "У аккаунта включена 2FA. Отправь пароль следующим сообщением."
            ),
            reply_markup=get_account_2fa_keyboard(),
            parse_mode="Markdown",
        )
    except (PhoneCodeEmptyError, PhoneCodeInvalidError):
        await bot_edit_text_safe(
            message.bot,
            chat_id=message.chat.id,
            message_id=menu_message_id,
            text="❌ **Неверный код Telegram**\n\nПроверь код и отправь его ещё раз.",
            reply_markup=get_account_phone_keyboard(),
            parse_mode="Markdown",
        )
    except PhoneCodeExpiredError as e:
        logger.warning("Telegram login code expired for %s: %s", phone, e)
        await state.clear()
        await bot_edit_text_safe(
            message.bot,
            chat_id=message.chat.id,
            message_id=menu_message_id,
            text=f"❌ **Код Telegram устарел**\n\n{format_login_error(e)}",
            reply_markup=get_account_status_keyboard(is_authorized=False),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("Failed to sign in with Telegram login code: %s", e, exc_info=True)
        await bot_edit_text_safe(
            message.bot,
            chat_id=message.chat.id,
            message_id=menu_message_id,
            text=f"❌ **Не удалось войти по коду**\n\n{format_login_error(e)}",
            reply_markup=get_account_phone_keyboard(),
            parse_mode="Markdown",
        )
