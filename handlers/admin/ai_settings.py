"""Admin screens for choosing AI provider, model, and API key."""

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
    get_ai_models_keyboard,
    get_ai_settings_keyboard,
    get_back_to_ai_settings_keyboard,
)
from services.ai import AI_PROVIDER_LABELS, AI_PROVIDERS, get_ai_config, list_available_models

logger = logging.getLogger(__name__)
router = Router(name="admin_ai_settings")

MODELS_PER_PAGE = 8


def _mask_secret(value: str | None) -> str:
    """Hide the bulk of an API key while keeping a small recognisable hint."""
    if not value:
        return "не задан"
    if len(value) <= 8:
        return "задан"
    return f"{value[:4]}...{value[-4:]}"


# -- Settings overview --------------------------------------------------------

async def _render_ai_settings(
    callback: CallbackQuery, repo: BotRepository, answer_text: str | None = None
) -> None:
    """Render the AI provider / model / key overview screen."""
    config = await get_ai_config(repo)
    provider_label = AI_PROVIDER_LABELS[config.provider]
    text = (
        "🤖 **Настройки ИИ**\n\n"
        f"Провайдер: **{provider_label}**\n"
        f"Модель: `{config.model_name}`\n"
        f"API-ключ: `{_mask_secret(config.api_key)}`\n\n"
        "Выбери провайдера или измени модель/API-ключ для текущего провайдера."
    )
    await edit_text_safe(
        callback.message,
        text=text,
        reply_markup=get_ai_settings_keyboard(config.provider),
        parse_mode="Markdown",
    )
    await callback.answer(answer_text)


@router.callback_query(F.data == "ai_settings")
async def show_ai_settings(callback: CallbackQuery, repo: BotRepository, state: FSMContext) -> None:
    await state.clear()
    await _render_ai_settings(callback, repo)


@router.callback_query(F.data.startswith("ai_provider:"))
async def set_ai_provider(callback: CallbackQuery, repo: BotRepository) -> None:
    provider = callback.data.split(":", 1)[1]
    if provider not in AI_PROVIDERS:
        await callback.answer("Неизвестный провайдер", show_alert=True)
        return

    await repo.settings.set("ai_provider", provider)
    await _render_ai_settings(callback, repo, answer_text=f"Провайдер: {AI_PROVIDER_LABELS[provider]}")


# -- Model selection ----------------------------------------------------------

async def _render_ai_models(
    callback: CallbackQuery,
    repo: BotRepository,
    *,
    page: int = 0,
    answer_text: str | None = None,
) -> None:
    """Render the paginated list of models available for the active provider."""
    config = await get_ai_config(repo)
    models = await list_available_models(config)

    max_page = max(0, (len(models) - 1) // MODELS_PER_PAGE) if models else 0
    page = min(max(page, 0), max_page)
    page_models = models[page * MODELS_PER_PAGE:(page + 1) * MODELS_PER_PAGE]

    model_lines = "\n".join(f"• `{model}`" for model in page_models)
    if not model_lines:
        model_lines = "Не удалось получить список моделей."

    await edit_text_safe(
        callback.message,
        text=(
            f"🧠 **Модель для {AI_PROVIDER_LABELS[config.provider]}**\n\n"
            f"Текущая модель: `{config.model_name}`\n\n"
            f"{model_lines}\n\n"
            "Выбери модель из списка или нажми ручной ввод."
        ),
        reply_markup=get_ai_models_keyboard(models, config.model_name, page=page, per_page=MODELS_PER_PAGE),
        parse_mode="Markdown",
    )
    await callback.answer(answer_text)


@router.callback_query(F.data == "ai_edit_model")
async def start_ai_model_edit(callback: CallbackQuery, repo: BotRepository, state: FSMContext) -> None:
    await state.clear()
    await _render_ai_models(callback, repo, page=0)


@router.callback_query(F.data.startswith("ai_models_page:"))
async def change_ai_models_page(callback: CallbackQuery, repo: BotRepository) -> None:
    page_value = callback.data.split(":", 1)[1]
    if page_value == "noop":
        await callback.answer()
        return

    try:
        page = int(page_value)
    except ValueError:
        await callback.answer("Некорректная страница", show_alert=True)
        return

    await _render_ai_models(callback, repo, page=page)


@router.callback_query(F.data.startswith("ai_model:"))
async def save_ai_model_from_list(callback: CallbackQuery, repo: BotRepository) -> None:
    config = await get_ai_config(repo)
    try:
        model_index = int(callback.data.split(":", 1)[1])
    except (TypeError, ValueError):
        await callback.answer("Некорректный выбор модели", show_alert=True)
        return

    models = await list_available_models(config)
    if model_index < 0 or model_index >= len(models):
        await callback.answer("Этой модели нет в текущем списке", show_alert=True)
        return

    model_name = models[model_index]
    await repo.settings.set(f"{config.provider}_model", model_name)
    await _render_ai_settings(callback, repo, answer_text=f"Модель: {model_name}")


# -- Manual model entry -------------------------------------------------------

@router.callback_query(F.data == "ai_model_manual")
async def start_ai_model_manual_edit(callback: CallbackQuery, repo: BotRepository, state: FSMContext) -> None:
    config = await get_ai_config(repo)
    await state.set_state(AdminStates.waiting_for_ai_model)
    await state.update_data(menu_message_id=callback.message.message_id, ai_provider=config.provider)

    await edit_text_safe(
        callback.message,
        text=(
            f"🧠 **Модель для {AI_PROVIDER_LABELS[config.provider]}**\n\n"
            f"Текущее значение: `{config.model_name}`\n\n"
            "Отправь новое название модели следующим сообщением."
        ),
        reply_markup=get_back_to_ai_settings_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


def _is_valid_model_name(value: str) -> bool:
    """Reject names with whitespace or backticks that break Markdown rendering."""
    return len(value) >= 2 and not any(ch.isspace() for ch in value) and "`" not in value


def _make_ai_model_validator(repo: BotRepository, provider: str):
    async def validate(raw: str) -> EditOutcome:
        if not _is_valid_model_name(raw):
            return EditOutcome(
                "❌ Название модели выглядит некорректно. Отправь model id без пробелов.",
                saved=False,
            )
        await repo.settings.set(f"{provider}_model", raw)
        return EditOutcome(
            f"✅ Модель сохранена: `{raw}`",
            parse_mode="Markdown",
        )

    return validate


@router.message(AdminStates.waiting_for_ai_model, F.chat.type == "private")
async def save_ai_model(message: Message, repo: BotRepository, state: FSMContext) -> None:
    if not await verify_admin(message, repo):
        return

    data = await state.get_data()
    provider = data.get("ai_provider")
    if provider not in AI_PROVIDERS:
        await state.clear()
        await message.answer("❌ Сессия настройки модели истекла.", reply_markup=get_back_to_ai_settings_keyboard())
        return

    await finalize_setting_edit(
        message,
        state,
        validator=_make_ai_model_validator(repo, provider),
        fallback_keyboard=get_back_to_ai_settings_keyboard(),
        expired_text="❌ Сессия настройки модели истекла.",
    )


# -- API key entry ------------------------------------------------------------

@router.callback_query(F.data == "ai_edit_key")
async def start_ai_key_edit(callback: CallbackQuery, repo: BotRepository, state: FSMContext) -> None:
    config = await get_ai_config(repo)
    await state.set_state(AdminStates.waiting_for_ai_key)
    await state.update_data(menu_message_id=callback.message.message_id, ai_provider=config.provider)

    await edit_text_safe(
        callback.message,
        text=(
            f"🔐 **API-ключ для {AI_PROVIDER_LABELS[config.provider]}**\n\n"
            f"Сейчас: `{_mask_secret(config.api_key)}`\n\n"
            "Отправь новый ключ следующим сообщением. Сообщение с ключом будет удалено из чата."
        ),
        reply_markup=get_back_to_ai_settings_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


def _is_valid_api_key(value: str) -> bool:
    """Catch the most common mistakes pasted instead of an API key."""
    return len(value) >= 10 and "YOUR_" not in value


def _make_ai_key_validator(repo: BotRepository, provider: str):
    async def validate(raw: str) -> EditOutcome:
        if not _is_valid_api_key(raw):
            return EditOutcome(
                "❌ Ключ выглядит некорректно. Проверь значение и отправь его еще раз.",
                saved=False,
            )
        await repo.settings.set(f"{provider}_api_key", raw)
        return EditOutcome(
            f"✅ API-ключ для {AI_PROVIDER_LABELS[provider]} сохранен: `{_mask_secret(raw)}`",
            parse_mode="Markdown",
        )

    return validate


@router.message(AdminStates.waiting_for_ai_key, F.chat.type == "private")
async def save_ai_key(message: Message, repo: BotRepository, state: FSMContext) -> None:
    if not await verify_admin(message, repo):
        return

    data = await state.get_data()
    provider = data.get("ai_provider")
    if provider not in AI_PROVIDERS:
        await state.clear()
        await message.answer("❌ Сессия настройки ключа истекла.", reply_markup=get_back_to_ai_settings_keyboard())
        return

    await finalize_setting_edit(
        message,
        state,
        validator=_make_ai_key_validator(repo, provider),
        fallback_keyboard=get_back_to_ai_settings_keyboard(),
        expired_text="❌ Сессия настройки ключа истекла.",
    )
