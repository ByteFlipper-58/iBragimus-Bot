"""The admin main menu, AI toggle, statistics, and connection guide."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import settings
from database.repository import BotRepository
from handlers.admin.context import get_account_status, get_ai_enabled, verify_admin
from handlers.admin.login_session import cancel_login, delete_qr_message
from handlers.admin.ui import edit_text_safe
from keyboards import get_back_keyboard, get_main_keyboard

router = Router(name="admin_menu")


def _main_menu_text(short: bool = False) -> str:
    """Return the main admin panel text."""
    if short:
        return "💼 **Панель управления iBragimusBot**\n\nВыбери нужное действие в меню ниже."

    return (
        "💼 **Панель управления iBragimusBot**\n\n"
        "Здесь можно управлять автоответами, промптом ИИ, черным списком "
        "и подключением аккаунта Telegram.\n\n"
        "Выбери нужное действие в меню ниже."
    )


def _format_stats(stats: dict, connections: list[dict]) -> str:
    """Compose the high-level statistics screen text."""
    if connections:
        conn_status = f"✅ Активно (всего профилей: {len(connections)})"
    else:
        conn_status = "❌ Нет активных подключений"

    return (
        "📊 **Статистика iBragimusBot**\n\n"
        f"🔗 **Состояние профиля:** {conn_status}\n"
        f"📩 **Обработано сообщений:** {stats['total_messages_processed']}\n"
        f"🤖 **Отправлено автоответов:** {stats['total_replies_sent']}\n"
        f"👥 **Активных чатов:** {stats['active_chats_count']}\n"
        f"🚫 **В черном списке:** {stats['blacklisted_count']} пользователей\n"
    )


def _connection_help_text() -> str:
    """Return the Telegram Business connection instructions."""
    return (
        "⚙️ **Как подключить iBragimusBot к профилю**\n\n"
        "1️⃣ **Включи Business Mode:**\n"
        "• Открой официальный бот @BotFather.\n"
        "• Отправь команду `/mybots` и выбери этого бота.\n"
        "• Перейди в **Bot Settings** → **Business Mode**.\n"
        "• Нажми **Turn on**, чтобы активировать режим.\n\n"
        "2️⃣ **Подключи бота в своем приложении Telegram:**\n"
        "• Открой настройки Telegram (на телефоне или компьютере).\n"
        "• Перейди в раздел **Telegram Business** → **Чат-боты** (Chatbots).\n"
        "• Введи юзернейм этого бота и добавь его.\n"
        "• Разреши боту отвечать на сообщения (`can_reply`).\n\n"
        "После этого iBragimusBot получит доступ к Business-чатам и сможет работать с сообщениями."
    )


async def _cleanup_login_artifacts(bot, chat_id: int, admin_id: int, state: FSMContext) -> None:
    """Drop any pending QR images and login tasks before showing the menu again."""
    data = await state.get_data()
    await delete_qr_message(bot, chat_id, data.get("qr_message_id"))
    await cancel_login(admin_id)
    await state.clear()


@router.message(CommandStart(), F.chat.type == "private")
@router.message(Command("menu"), F.chat.type == "private")
async def show_main_menu(
    message: Message,
    repo: BotRepository,
    state: FSMContext,
) -> None:
    """Open the private admin panel."""
    if not await verify_admin(message, repo):
        return

    await _cleanup_login_artifacts(message.bot, message.chat.id, settings.ADMIN_ID, state)

    await message.answer(
        text=_main_menu_text(),
        reply_markup=get_main_keyboard(
            await get_ai_enabled(repo),
            await get_account_status(),
        ),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "back_to_menu")
async def return_to_main_menu(
    callback: CallbackQuery,
    repo: BotRepository,
    state: FSMContext,
) -> None:
    """Return from a nested admin screen to the main panel."""
    await _cleanup_login_artifacts(
        callback.message.bot, callback.message.chat.id, callback.from_user.id, state
    )

    await edit_text_safe(
        callback.message,
        text=_main_menu_text(short=True),
        reply_markup=get_main_keyboard(
            await get_ai_enabled(repo),
            await get_account_status(),
        ),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_ai")
async def toggle_ai_replies(
    callback: CallbackQuery,
    repo: BotRepository,
) -> None:
    """Toggle AI auto-replies for Business chats."""
    current_state = await repo.settings.get("ai_enabled", "1")
    new_state = "0" if current_state == "1" else "1"
    await repo.settings.set("ai_enabled", new_state)

    ai_enabled = new_state == "1"
    status_msg = "включены" if ai_enabled else "выключены"

    await callback.message.edit_reply_markup(
        reply_markup=get_main_keyboard(
            ai_enabled,
            await get_account_status(),
        )
    )
    await callback.answer(f"✅ Автоответы ИИ {status_msg}!")


@router.callback_query(F.data == "view_stats")
async def show_stats(callback: CallbackQuery, repo: BotRepository) -> None:
    """Show high-level bot usage statistics."""
    stats = await repo.logs.get_stats()
    connections = await repo.connections.get_active()

    await callback.message.edit_text(
        text=_format_stats(stats, connections),
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "how_to_connect")
async def show_connection_help(callback: CallbackQuery) -> None:
    """Show Telegram Business connection instructions."""
    await callback.message.edit_text(
        text=_connection_help_text(),
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()
