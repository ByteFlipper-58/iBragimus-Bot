"""Manage the chat/user blacklist from the admin panel."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.repository import BotRepository
from handlers.admin.context import verify_admin
from handlers.admin.fsm_input import EditOutcome, finalize_setting_edit
from handlers.admin.states import AdminStates
from handlers.admin.ui import edit_text_safe
from keyboards import get_back_to_blacklist_keyboard

logger = logging.getLogger(__name__)
router = Router(name="admin_blacklist")

DISPLAY_LIMIT = 15
REMOVAL_LIMIT = 10
DEFAULT_REASON = "Добавлен вручную"


def _format_blacklist_text(blacklist: list[dict]) -> str:
    """Compose the human-readable summary of the blacklist."""
    text = "🚫 **Черный список пользователей**\n\n"
    if not blacklist:
        return text + "Список пуст. Бот отвечает всем пользователям."

    text += "Бот полностью игнорирует сообщения от следующих пользователей:\n\n"
    for item in blacklist[:DISPLAY_LIMIT]:
        username_str = f" (@{item['username']})" if item["username"] else ""
        text += f"• `{item['chat_id']}`{username_str} — {item['reason'] or 'без причины'}\n"

    if len(blacklist) > DISPLAY_LIMIT:
        text += f"\n_...и еще {len(blacklist) - DISPLAY_LIMIT} записей._"
    return text


def _blacklist_root_keyboard() -> InlineKeyboardMarkup:
    """Top-level keyboard for the blacklist root screen."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить в ЧС", callback_data="add_to_blacklist"),
            InlineKeyboardButton(text="➖ Удалить из ЧС", callback_data="remove_from_blacklist"),
        ],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu")],
    ])


@router.callback_query(F.data == "manage_blacklist")
async def show_blacklist_menu(
    callback: CallbackQuery,
    repo: BotRepository,
    state: FSMContext | None = None,
) -> None:
    """Show blacklist entries and management actions."""
    if state:
        await state.clear()

    blacklist = await repo.blacklist.all()
    await edit_text_safe(
        callback.message,
        text=_format_blacklist_text(blacklist),
        reply_markup=_blacklist_root_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "add_to_blacklist")
async def start_blacklist_add(callback: CallbackQuery, state: FSMContext) -> None:
    """Switch the admin panel into blacklist add mode."""
    await state.set_state(AdminStates.waiting_for_blacklist_id)
    await state.update_data(menu_message_id=callback.message.message_id)
    await edit_text_safe(
        callback.message,
        text=(
            "➕ **Добавление в черный список**\n\n"
            "Пожалуйста, пришлите Telegram **ID пользователя** (число) или перешлите сообщение от него.\n"
            "Вы также можете написать в формате: `ID причина_блокировки`"
        ),
        reply_markup=get_back_to_blacklist_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


def _parse_blacklist_input(message: Message) -> tuple[int | None, str | None, str]:
    """Parse the admin reply into ``(target_id, username, reason)``.

    ``target_id`` is ``None`` when the reply could not be interpreted; the
    caller renders an error message in that case.
    """
    if message.forward_from:
        return message.forward_from.id, message.forward_from.username, DEFAULT_REASON

    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    if parts and parts[0].isdigit():
        reason = parts[1] if len(parts) > 1 else DEFAULT_REASON
        return int(parts[0]), None, reason

    return None, None, DEFAULT_REASON


def _make_blacklist_add_validator(repo: BotRepository, message: Message):
    async def validate(_: str) -> EditOutcome:
        target_id, username, reason = _parse_blacklist_input(message)
        if target_id is None:
            error_text = "❌ Неверный формат. Пожалуйста, отправьте корректное числовое ID пользователя."
            if message.forward_sender_name:
                error_text = (
                    "❌ Пересланный пользователь скрыл свои данные конфиденциальности. "
                    "Пожалуйста, введите его ID числом."
                )
            return EditOutcome(error_text, saved=False)

        await repo.blacklist.add(chat_id=target_id, username=username, reason=reason)
        return EditOutcome(
            f"✅ Пользователь `{target_id}` успешно добавлен в черный список!",
            parse_mode="Markdown",
        )

    return validate


@router.message(AdminStates.waiting_for_blacklist_id, F.chat.type == "private")
async def add_blacklist_entry(message: Message, repo: BotRepository, state: FSMContext) -> None:
    """Parse an admin message and add a Telegram user ID to the blacklist."""
    if not await verify_admin(message, repo):
        return
    await finalize_setting_edit(
        message,
        state,
        validator=_make_blacklist_add_validator(repo, message),
        fallback_keyboard=get_back_to_blacklist_keyboard(),
        expired_text="❌ Сессия черного списка истекла. Открой меню заново.",
    )


@router.callback_query(F.data == "remove_from_blacklist")
async def show_blacklist_remove_menu(callback: CallbackQuery, repo: BotRepository) -> None:
    """Show a short list of blacklist entries that can be removed."""
    blacklist = await repo.blacklist.all()

    if not blacklist:
        await edit_text_safe(
            callback.message,
            text="🚫 Черный список пуст, нечего удалять.",
            reply_markup=get_back_to_blacklist_keyboard(),
        )
        return

    keyboard: list[list[InlineKeyboardButton]] = []
    for item in blacklist[:REMOVAL_LIMIT]:
        username_str = f" @{item['username']}" if item["username"] else f" ID: {item['chat_id']}"
        keyboard.append([
            InlineKeyboardButton(text=f"❌ Удалить {username_str}", callback_data=f"del_bl_{item['chat_id']}")
        ])

    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="manage_blacklist")])

    await edit_text_safe(
        callback.message,
        text="➖ **Выберите пользователя для удаления из черного списка:**",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("del_bl_"))
async def delete_blacklist_entry(callback: CallbackQuery, repo: BotRepository) -> None:
    """Remove a Telegram user ID from the blacklist."""
    raw_id = callback.data.removeprefix("del_bl_")
    try:
        chat_id = int(raw_id)
    except ValueError:
        await callback.answer("❌ Некорректный идентификатор записи.", show_alert=True)
        return

    deleted = await repo.blacklist.remove(chat_id)

    if deleted:
        await callback.answer("✅ Пользователь удален из черного списка!")
    else:
        await callback.answer("❌ Не удалось найти пользователя.")

    await show_blacklist_remove_menu(callback, repo)
