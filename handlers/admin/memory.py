"""Admin screen: persona (owner bio) and per-contact memory notes."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.repository import BotRepository
from handlers.admin.context import verify_admin
from handlers.admin.fsm_input import EditOutcome, finalize_setting_edit
from handlers.admin.states import AdminStates
from handlers.admin.ui import edit_text_safe
from keyboards import (
    get_back_to_memory_keyboard,
    get_chat_note_keyboard,
    get_memory_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="admin_memory")

MAX_BIO_LENGTH = 2000
MAX_NOTE_LENGTH = 2000
NOTES_PREVIEW = 80


def _escape_md(text: str) -> str:
    """Escape backticks so we can safely wrap user text in code blocks."""
    return text.replace("`", "ʼ")


# -- Memory landing screen ----------------------------------------------------

async def _render_memory_menu(callback: CallbackQuery, repo: BotRepository) -> None:
    bio = await repo.settings.get("owner_bio", "") or ""
    notes = await repo.chat_notes.list_recent(limit=1)

    bio_status = f"`{len(bio)}` символов" if bio else "не задана"
    notes_status = "есть записи" if notes else "пусто"

    text = (
        "🧠 **Память и личность**\n\n"
        "Здесь хранится контекст, который ИИ подмешивает в каждый ответ:\n"
        "• «О себе» — факты про владельца аккаунта (имя, работа, привычки).\n"
        "• Заметки о собеседнике — что бот должен помнить про конкретный чат.\n\n"
        f"🪪 О себе: {bio_status}\n"
        f"📒 Заметки о собеседниках: {notes_status}"
    )
    await edit_text_safe(
        callback.message,
        text=text,
        reply_markup=get_memory_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "memory_menu")
async def show_memory_menu(callback: CallbackQuery, repo: BotRepository, state: FSMContext) -> None:
    await state.clear()
    await _render_memory_menu(callback, repo)


# -- Owner bio ----------------------------------------------------------------

@router.callback_query(F.data == "memory_bio_view")
async def view_owner_bio(callback: CallbackQuery, repo: BotRepository) -> None:
    bio = await repo.settings.get("owner_bio", "") or ""
    if bio:
        text = f"🪪 **Биография владельца**\n\n`{_escape_md(bio)}`"
    else:
        text = (
            "🪪 **Биография владельца**\n\n"
            "Пока ничего не задано. Нажми «Изменить «о себе»», чтобы рассказать ИИ, "
            "кто такой владелец аккаунта (имя, профессия, манера речи, важные факты)."
        )
    await edit_text_safe(
        callback.message,
        text=text,
        reply_markup=get_back_to_memory_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "memory_bio_edit")
async def start_owner_bio_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_for_owner_bio)
    await state.update_data(menu_message_id=callback.message.message_id)
    await edit_text_safe(
        callback.message,
        text=(
            "🪪 **Биография владельца**\n\n"
            "Опиши свободным текстом, что ИИ должен знать про тебя — имя, "
            "город, работу, увлечения, манеру общения, имена близких. "
            "Это будет добавляться в контекст каждого ответа.\n\n"
            f"Лимит — {MAX_BIO_LENGTH} символов. Чтобы очистить, отправь `-`."
        ),
        reply_markup=get_back_to_memory_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


def _make_owner_bio_validator(repo: BotRepository):
    async def validate(raw: str) -> EditOutcome:
        if raw == "-":
            await repo.settings.set("owner_bio", "")
            return EditOutcome("✅ Биография очищена.")

        if len(raw) > MAX_BIO_LENGTH:
            return EditOutcome(
                f"❌ Слишком длинно. Максимум {MAX_BIO_LENGTH} символов.",
                saved=False,
            )

        await repo.settings.set("owner_bio", raw)
        return EditOutcome(
            f"✅ **Биография сохранена** ({len(raw)} симв.).\n\n`{_escape_md(raw)}`",
            parse_mode="Markdown",
        )

    return validate


@router.message(AdminStates.waiting_for_owner_bio, F.chat.type == "private")
async def save_owner_bio(message: Message, repo: BotRepository, state: FSMContext) -> None:
    if not await verify_admin(message, repo):
        return
    await finalize_setting_edit(
        message,
        state,
        validator=_make_owner_bio_validator(repo),
        fallback_keyboard=get_back_to_memory_keyboard(),
    )


# -- Per-chat notes -----------------------------------------------------------

def _format_notes_list(notes: list[dict]) -> str:
    if not notes:
        return (
            "📒 **Заметки о собеседниках**\n\n"
            "Пока пусто. Используй кнопку «Добавить заметку по chat_id», "
            "чтобы записать что бот должен помнить про конкретного человека.\n\n"
            "💡 chat_id собеседника можно подсмотреть в разделе статистики/логов "
            "или в самом архиве сообщений."
        )

    lines = ["📒 **Заметки о собеседниках**\n"]
    for note in notes:
        chat_id = note["chat_id"]
        text = (note.get("notes") or "").strip().replace("\n", " ")
        if len(text) > NOTES_PREVIEW:
            text = text[: NOTES_PREVIEW - 1] + "…"
        lines.append(f"• `{chat_id}` — {_escape_md(text)}")
    lines.append("\nЧтобы открыть заметку, отправь её chat_id (или нажми «Добавить»).")
    return "\n".join(lines)


@router.callback_query(F.data == "memory_notes_list")
async def show_notes_list(callback: CallbackQuery, repo: BotRepository, state: FSMContext) -> None:
    await state.clear()
    notes = await repo.chat_notes.list_recent(limit=20)
    await edit_text_safe(
        callback.message,
        text=_format_notes_list(notes),
        reply_markup=get_back_to_memory_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "memory_notes_add")
async def start_note_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_for_chat_note_id)
    await state.update_data(menu_message_id=callback.message.message_id)
    await edit_text_safe(
        callback.message,
        text=(
            "➕ **Новая заметка по chat_id**\n\n"
            "Отправь Telegram chat_id собеседника (целое число). "
            "Если у этого чата уже есть заметка — её можно будет перезаписать."
        ),
        reply_markup=get_back_to_memory_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_chat_note_id, F.chat.type == "private")
async def receive_chat_id_for_note(
    message: Message, repo: BotRepository, state: FSMContext
) -> None:
    if not await verify_admin(message, repo):
        return

    raw = (message.text or "").strip()
    try:
        await message.delete()
    except Exception:
        pass

    data = await state.get_data()
    menu_message_id = data.get("menu_message_id")

    try:
        chat_id = int(raw)
    except ValueError:
        if menu_message_id:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=menu_message_id,
                text="❌ Нужно целое число chat_id. Попробуй снова.",
                reply_markup=get_back_to_memory_keyboard(),
                parse_mode="Markdown",
            )
        return

    existing = await repo.chat_notes.get(chat_id)
    await state.set_state(AdminStates.waiting_for_chat_note_text)
    await state.update_data(chat_note_id=chat_id, menu_message_id=menu_message_id)

    preview = f"`{_escape_md(existing)}`" if existing else "_пусто_"
    if menu_message_id:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=menu_message_id,
            text=(
                f"📝 **Заметка для chat_id `{chat_id}`**\n\n"
                f"Текущее содержимое: {preview}\n\n"
                "Пришли новый текст заметки. Чтобы удалить заметку, отправь `-`.\n"
                f"Лимит — {MAX_NOTE_LENGTH} символов."
            ),
            reply_markup=get_back_to_memory_keyboard(),
            parse_mode="Markdown",
        )


def _make_chat_note_validator(repo: BotRepository, chat_id: int):
    async def validate(raw: str) -> EditOutcome:
        if raw == "-":
            await repo.chat_notes.delete(chat_id)
            return EditOutcome(
                f"🗑 Заметка для `{chat_id}` удалена.",
                parse_mode="Markdown",
            )

        if not raw:
            return EditOutcome("❌ Пустой текст. Пришли заметку или `-` для удаления.", saved=False)

        if len(raw) > MAX_NOTE_LENGTH:
            return EditOutcome(
                f"❌ Слишком длинно. Максимум {MAX_NOTE_LENGTH} символов.",
                saved=False,
            )

        await repo.chat_notes.set(chat_id, raw)
        return EditOutcome(
            f"✅ Заметка для `{chat_id}` сохранена.\n\n`{_escape_md(raw)}`",
            parse_mode="Markdown",
        )

    return validate


@router.message(AdminStates.waiting_for_chat_note_text, F.chat.type == "private")
async def save_chat_note(
    message: Message, repo: BotRepository, state: FSMContext
) -> None:
    if not await verify_admin(message, repo):
        return

    data = await state.get_data()
    chat_id = data.get("chat_note_id")
    if chat_id is None:
        await state.clear()
        await message.answer(
            "❌ Сессия редактирования заметки истекла. Открой меню заново.",
            reply_markup=get_back_to_memory_keyboard(),
        )
        return

    await finalize_setting_edit(
        message,
        state,
        validator=_make_chat_note_validator(repo, int(chat_id)),
        fallback_keyboard=get_back_to_memory_keyboard(),
        expired_text="❌ Сессия редактирования заметки истекла.",
    )


# -- Per-note quick actions (edit / delete by callback) ----------------------

@router.callback_query(F.data.startswith("memory_note_edit:"))
async def quick_edit_note(callback: CallbackQuery, state: FSMContext) -> None:
    chat_id = int(callback.data.split(":", 1)[1])
    await state.set_state(AdminStates.waiting_for_chat_note_text)
    await state.update_data(
        chat_note_id=chat_id,
        menu_message_id=callback.message.message_id,
    )
    await edit_text_safe(
        callback.message,
        text=(
            f"✏️ Изменение заметки для chat_id `{chat_id}`.\n\n"
            f"Пришли новый текст или `-` для удаления."
        ),
        reply_markup=get_back_to_memory_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("memory_note_delete:"))
async def quick_delete_note(callback: CallbackQuery, repo: BotRepository) -> None:
    chat_id = int(callback.data.split(":", 1)[1])
    await repo.chat_notes.delete(chat_id)
    await callback.answer("Заметка удалена.")
    notes = await repo.chat_notes.list_recent(limit=20)
    await edit_text_safe(
        callback.message,
        text=_format_notes_list(notes),
        reply_markup=get_back_to_memory_keyboard(),
        parse_mode="Markdown",
    )


# -- Owner writing style ------------------------------------------------------

@router.callback_query(F.data == "memory_style_view")
async def view_owner_style(callback: CallbackQuery, repo: BotRepository) -> None:
    """Show the auto-mined writing style for the owner."""
    style = await repo.settings.get("owner_style", "") or ""
    updated = await repo.settings.get("owner_style_updated_at", "") or "—"

    if style:
        text = (
            "🎨 **Стиль владельца**\n\n"
            f"Обновлён: `{updated}`\n\n"
            f"`{_escape_md(style)}`"
        )
    else:
        text = (
            "🎨 **Стиль владельца**\n\n"
            "Профиль ещё не собран. Бот формирует его автоматически из твоих "
            "собственных сообщений в Business-чатах. Появится после того, "
            "как накопится хотя бы 12 твоих исходящих сообщений, либо "
            "нажми «Пересобрать стиль»."
        )

    from keyboards import get_back_to_memory_keyboard as _back

    await edit_text_safe(
        callback.message,
        text=text,
        reply_markup=_back(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "memory_style_refresh")
async def refresh_owner_style(callback: CallbackQuery, repo: BotRepository) -> None:
    """Force-rebuild the owner-style profile right now."""
    from config import settings as app_settings
    from services.ai.jobs import refresh_owner_style_if_needed

    settings_map = await repo.settings.all()
    await callback.answer("Запускаю...")
    await refresh_owner_style_if_needed(
        repo,
        settings_map=settings_map,
        owner_id=app_settings.ADMIN_ID,
        force=True,
    )
    await view_owner_style(callback, repo)


# -- Auto-memory / summary settings -------------------------------------------

from keyboards import get_auto_memory_keyboard


def _auto_settings_text(settings_map: dict[str, str]) -> str:
    auto_enabled = settings_map.get("auto_memory_enabled", "1") == "1"
    summary_enabled = settings_map.get("summary_enabled", "1") == "1"
    every_n = settings_map.get("auto_memory_every_n", "10")
    summary_threshold = settings_map.get("summary_threshold", "30")

    return (
        "🧠 **Авто-память и сводка**\n\n"
        f"Авто-память: {'включена' if auto_enabled else 'выключена'} "
        f"(каждые `{every_n}` новых сообщений в чате).\n"
        f"Сводка диалога: {'включена' if summary_enabled else 'выключена'} "
        f"(порог `{summary_threshold}` сообщений).\n\n"
        "Авто-память сама дописывает заметки о собеседнике на основе свежих "
        "сообщений. Сводка сжимает старую часть длинного диалога в одну строку, "
        "чтобы у бота оставалась «дальняя память» без раздутого контекста."
    )


@router.callback_query(F.data == "memory_auto_view")
async def show_auto_settings(callback: CallbackQuery, repo: BotRepository) -> None:
    settings_map = await repo.settings.all()
    auto_enabled = settings_map.get("auto_memory_enabled", "1") == "1"
    summary_enabled = settings_map.get("summary_enabled", "1") == "1"
    await edit_text_safe(
        callback.message,
        text=_auto_settings_text(settings_map),
        reply_markup=get_auto_memory_keyboard(auto_enabled, summary_enabled),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "memory_auto_toggle")
async def toggle_auto_memory(callback: CallbackQuery, repo: BotRepository) -> None:
    current = await repo.settings.get("auto_memory_enabled", "1")
    await repo.settings.set("auto_memory_enabled", "0" if current == "1" else "1")
    await show_auto_settings(callback, repo)


@router.callback_query(F.data == "memory_summary_toggle")
async def toggle_summary(callback: CallbackQuery, repo: BotRepository) -> None:
    current = await repo.settings.get("summary_enabled", "1")
    await repo.settings.set("summary_enabled", "0" if current == "1" else "1")
    await show_auto_settings(callback, repo)
