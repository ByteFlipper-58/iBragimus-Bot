"""View and edit the system prompt used by the AI service."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.repository import BotRepository
from handlers.admin.context import verify_admin
from handlers.admin.fsm_input import EditOutcome, finalize_setting_edit
from handlers.admin.states import AdminStates
from handlers.admin.ui import edit_text_safe
from keyboards import get_back_keyboard

logger = logging.getLogger(__name__)
router = Router(name="admin_prompt")

MIN_PROMPT_LENGTH = 10


@router.callback_query(F.data == "view_prompt")
async def show_prompt(callback: CallbackQuery, repo: BotRepository) -> None:
    """Show the current system prompt in the admin panel."""
    prompt = await repo.settings.get("system_prompt", "Промпт не установлен.")

    await edit_text_safe(
        callback.message,
        text=f"📋 **Текущий промпт ИИ**\n\n`{prompt}`",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "edit_prompt")
async def start_prompt_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """Switch the admin panel into system prompt edit mode."""
    await state.set_state(AdminStates.waiting_for_prompt)
    await state.update_data(menu_message_id=callback.message.message_id)
    await edit_text_safe(
        callback.message,
        text=(
            "✏️ **Изменение промпта ИИ**\n\n"
            "Отправь боту новое текстовое руководство (системную инструкцию). "
            "Например:\n"
            "_\"Ты занятой разработчик. Отвечай кратко, с юмором. Скажи, что ответишь вечером.\"_\n\n"
            "Напиши новый промпт следующим сообщением или нажми кнопку отмены."
        ),
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


def _make_prompt_validator(repo: BotRepository):
    async def validate(raw: str) -> EditOutcome:
        if len(raw) < MIN_PROMPT_LENGTH:
            return EditOutcome(
                "❌ Промпт слишком короткий. Пожалуйста, напишите более подробную инструкцию "
                f"(минимум {MIN_PROMPT_LENGTH} символов).",
                saved=False,
            )

        await repo.settings.set("system_prompt", raw)
        return EditOutcome(
            f"✅ **Системный промпт успешно сохранен!**\n\nНовое значение:\n`{raw}`",
            parse_mode="Markdown",
        )

    return validate


@router.message(AdminStates.waiting_for_prompt, F.chat.type == "private")
async def save_prompt(message: Message, repo: BotRepository, state: FSMContext) -> None:
    """Validate and save a new system prompt from the admin chat."""
    if not await verify_admin(message, repo):
        return
    await finalize_setting_edit(
        message,
        state,
        validator=_make_prompt_validator(repo),
        fallback_keyboard=get_back_keyboard(),
        expired_text="❌ Сессия редактирования промпта истекла. Открой меню заново.",
    )
