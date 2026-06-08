"""Auto-reply behaviour settings: delay, ignored words, conversation context."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.repository import BotRepository
from handlers.admin.context import verify_admin
from handlers.admin.fsm_input import EditOutcome, finalize_setting_edit
from handlers.admin.states import AdminStates
from handlers.admin.ui import edit_text_safe
from keyboards import get_back_to_behavior_keyboard, get_behavior_settings_keyboard

logger = logging.getLogger(__name__)
router = Router(name="admin_behavior")

MAX_REPLY_DELAY = 3600
MAX_CONTEXT_LIMIT = 20
MAX_DEBOUNCE_SECONDS = 120
MAX_OWNER_PAUSE_MINUTES = 24 * 60


async def _render_behavior_settings(
    callback: CallbackQuery,
    repo: BotRepository,
    answer_text: str | None = None,
) -> None:
    """Render the behaviour settings overview, reading current values once."""
    settings_map = await repo.settings.all()

    delay = settings_map.get("reply_delay_seconds", "0")
    ignored_words = settings_map.get("ignored_words", "")
    context_enabled = settings_map.get("ai_context_enabled", "1") == "1"
    context_limit = settings_map.get("ai_context_limit", "5")
    debounce_seconds = settings_map.get("debounce_seconds", "8")
    owner_pause = settings_map.get("owner_pause_minutes", "15")
    stop_word = settings_map.get("stop_word", "!стоп")
    resume_word = settings_map.get("resume_word", "!старт")
    toxicity_enabled = settings_map.get("toxicity_filter_enabled", "1") == "1"

    ignored_preview = ignored_words if ignored_words else "не заданы"
    context_state = "включен" if context_enabled else "выключен"
    toxicity_state = "включен" if toxicity_enabled else "выключен"

    text = (
        "⚙️ **Поведение автоответов**\n\n"
        f"⏱ Задержка ответа: `{delay}` сек.\n"
        f"⏳ Дебаунс серии: `{debounce_seconds}` сек.\n"
        f"🤐 Пауза при активности владельца: `{owner_pause}` мин.\n"
        f"🛑 Стоп-слово: `{stop_word or 'не задано'}` / "
        f"▶️ Старт-слово: `{resume_word or 'не задано'}`\n"
        f"🛡 Фильтр токсичности: `{toxicity_state}`\n"
        f"🙅 Игнорируемые слова: `{ignored_preview}`\n"
        f"🧠 Контекст диалога: `{context_state}`\n"
        f"🔢 Глубина контекста: `{context_limit}` сообщений\n\n"
        "Дебаунс склеивает несколько подряд идущих сообщений в один ответ. "
        "Пауза при активности владельца молчит, пока ты сам недавно писал в чате. "
        "Стоп-/старт-слова — твои короткие команды прямо в самом чате."
    )
    await edit_text_safe(
        callback.message,
        text=text,
        reply_markup=get_behavior_settings_keyboard(context_enabled, toxicity_enabled),
        parse_mode="Markdown",
    )
    await callback.answer(answer_text)


async def _start_edit(
    callback: CallbackQuery,
    state: FSMContext,
    *,
    fsm_state: AdminStates,
    text: str,
) -> None:
    """Switch the admin into an FSM-edit state and update the menu prompt."""
    await state.set_state(fsm_state)
    await state.update_data(menu_message_id=callback.message.message_id)
    await edit_text_safe(
        callback.message,
        text=text,
        reply_markup=get_back_to_behavior_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "behavior_settings")
async def show_behavior_settings(callback: CallbackQuery, repo: BotRepository, state: FSMContext) -> None:
    """Open the auto-reply behavior settings screen."""
    await state.clear()
    await _render_behavior_settings(callback, repo)


@router.callback_query(F.data == "behavior_toggle_context")
async def toggle_context(callback: CallbackQuery, repo: BotRepository) -> None:
    """Toggle whether prior conversation turns are sent to the AI."""
    current = await repo.settings.get("ai_context_enabled", "1")
    new_state = "0" if current == "1" else "1"
    await repo.settings.set("ai_context_enabled", new_state)
    status = "включён" if new_state == "1" else "выключен"
    await _render_behavior_settings(callback, repo, answer_text=f"Контекст диалога {status}")


# -- Reply delay --------------------------------------------------------------

@router.callback_query(F.data == "behavior_delay")
async def start_delay_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await _start_edit(
        callback,
        state,
        fsm_state=AdminStates.waiting_for_reply_delay,
        text=(
            "⏱ **Задержка ответа**\n\n"
            f"Отправь число секунд (от 0 до {MAX_REPLY_DELAY}).\n"
            "0 — отвечать сразу."
        ),
    )


def _make_delay_validator(repo: BotRepository):
    async def validate(raw: str) -> EditOutcome:
        try:
            delay = int(raw)
        except ValueError:
            return EditOutcome("❌ Нужно целое число секунд. Попробуй ещё раз.", saved=False)

        if delay < 0 or delay > MAX_REPLY_DELAY:
            return EditOutcome(
                f"❌ Значение должно быть от 0 до {MAX_REPLY_DELAY} секунд.",
                saved=False,
            )

        await repo.settings.set("reply_delay_seconds", str(delay))
        return EditOutcome(
            f"✅ Задержка ответа сохранена: `{delay}` сек.",
            parse_mode="Markdown",
        )

    return validate


@router.message(AdminStates.waiting_for_reply_delay, F.chat.type == "private")
async def save_delay(message: Message, repo: BotRepository, state: FSMContext) -> None:
    if not await verify_admin(message, repo):
        return
    await finalize_setting_edit(
        message,
        state,
        validator=_make_delay_validator(repo),
        fallback_keyboard=get_back_to_behavior_keyboard(),
    )


# -- Ignored words ------------------------------------------------------------

@router.callback_query(F.data == "behavior_ignored")
async def start_ignored_edit(callback: CallbackQuery, repo: BotRepository, state: FSMContext) -> None:
    current = await repo.settings.get("ignored_words", "")
    await _start_edit(
        callback,
        state,
        fsm_state=AdminStates.waiting_for_ignored_words,
        text=(
            "🙅 **Игнорируемые слова**\n\n"
            f"Текущий список: `{current or 'пусто'}`\n\n"
            "Отправь слова через запятую. Если сообщение содержит любое из них, "
            "бот не будет на него отвечать.\n"
            "Чтобы очистить список, отправь `-`."
        ),
    )


def _normalize_ignored_words(raw: str) -> str:
    """Lowercase, dedupe, and join ignored words. ``-`` clears the list."""
    if raw == "-":
        return ""
    words = [word.strip().lower() for word in raw.split(",") if word.strip()]
    return ",".join(dict.fromkeys(words))


def _make_ignored_words_validator(repo: BotRepository):
    async def validate(raw: str) -> EditOutcome:
        normalized = _normalize_ignored_words(raw)
        await repo.settings.set("ignored_words", normalized)
        return EditOutcome(
            f"✅ Игнорируемые слова сохранены: `{normalized or 'пусто'}`",
            parse_mode="Markdown",
        )

    return validate


@router.message(AdminStates.waiting_for_ignored_words, F.chat.type == "private")
async def save_ignored_words(message: Message, repo: BotRepository, state: FSMContext) -> None:
    if not await verify_admin(message, repo):
        return
    await finalize_setting_edit(
        message,
        state,
        validator=_make_ignored_words_validator(repo),
        fallback_keyboard=get_back_to_behavior_keyboard(),
    )


# -- Context limit ------------------------------------------------------------

@router.callback_query(F.data == "behavior_context_limit")
async def start_context_limit_edit(callback: CallbackQuery, repo: BotRepository, state: FSMContext) -> None:
    current = await repo.settings.get("ai_context_limit", "5")
    await _start_edit(
        callback,
        state,
        fsm_state=AdminStates.waiting_for_context_limit,
        text=(
            "🔢 **Глубина контекста диалога**\n\n"
            f"Сейчас: `{current}` последних обменов.\n\n"
            f"Отправь число от 0 до {MAX_CONTEXT_LIMIT}. "
            "Это сколько прошлых пар «сообщение-ответ» передаётся ИИ.\n"
            "0 — отвечать без учёта истории."
        ),
    )


def _make_context_limit_validator(repo: BotRepository):
    async def validate(raw: str) -> EditOutcome:
        try:
            limit = int(raw)
        except ValueError:
            return EditOutcome("❌ Нужно целое число. Попробуй ещё раз.", saved=False)

        if limit < 0 or limit > MAX_CONTEXT_LIMIT:
            return EditOutcome(
                f"❌ Значение должно быть от 0 до {MAX_CONTEXT_LIMIT}.",
                saved=False,
            )

        await repo.settings.set("ai_context_limit", str(limit))
        return EditOutcome(
            f"✅ Глубина контекста сохранена: `{limit}` обменов.",
            parse_mode="Markdown",
        )

    return validate


@router.message(AdminStates.waiting_for_context_limit, F.chat.type == "private")
async def save_context_limit(message: Message, repo: BotRepository, state: FSMContext) -> None:
    if not await verify_admin(message, repo):
        return
    await finalize_setting_edit(
        message,
        state,
        validator=_make_context_limit_validator(repo),
        fallback_keyboard=get_back_to_behavior_keyboard(),
    )


# -- Debounce ------------------------------------------------------------------

@router.callback_query(F.data == "behavior_debounce")
async def start_debounce_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await _start_edit(
        callback,
        state,
        fsm_state=AdminStates.waiting_for_debounce,
        text=(
            "⏳ **Дебаунс серии сообщений**\n\n"
            f"Отправь число секунд (от 0 до {MAX_DEBOUNCE_SECONDS}).\n"
            "Бот ждёт это время после последнего сообщения собеседника, "
            "затем отвечает одним сообщением сразу на всю серию.\n"
            "0 — отвечать на каждое сообщение по отдельности."
        ),
    )


def _make_debounce_validator(repo: BotRepository):
    async def validate(raw: str) -> EditOutcome:
        try:
            value = int(raw)
        except ValueError:
            return EditOutcome("❌ Нужно целое число секунд. Попробуй ещё раз.", saved=False)
        if value < 0 or value > MAX_DEBOUNCE_SECONDS:
            return EditOutcome(
                f"❌ Значение должно быть от 0 до {MAX_DEBOUNCE_SECONDS} секунд.",
                saved=False,
            )
        await repo.settings.set("debounce_seconds", str(value))
        return EditOutcome(
            f"✅ Дебаунс сохранён: `{value}` сек.",
            parse_mode="Markdown",
        )

    return validate


@router.message(AdminStates.waiting_for_debounce, F.chat.type == "private")
async def save_debounce(message: Message, repo: BotRepository, state: FSMContext) -> None:
    if not await verify_admin(message, repo):
        return
    await finalize_setting_edit(
        message,
        state,
        validator=_make_debounce_validator(repo),
        fallback_keyboard=get_back_to_behavior_keyboard(),
    )


# -- Owner pause window --------------------------------------------------------

@router.callback_query(F.data == "behavior_owner_pause")
async def start_owner_pause_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await _start_edit(
        callback,
        state,
        fsm_state=AdminStates.waiting_for_owner_pause,
        text=(
            "🤐 **Пауза при активности владельца**\n\n"
            f"Отправь число минут (от 0 до {MAX_OWNER_PAUSE_MINUTES}).\n"
            "Если ты сам недавно писал в чате, бот молчит указанное число "
            "минут и не вмешивается.\n"
            "0 — выключить эту защиту."
        ),
    )


def _make_owner_pause_validator(repo: BotRepository):
    async def validate(raw: str) -> EditOutcome:
        try:
            value = int(raw)
        except ValueError:
            return EditOutcome("❌ Нужно целое число минут. Попробуй ещё раз.", saved=False)
        if value < 0 or value > MAX_OWNER_PAUSE_MINUTES:
            return EditOutcome(
                f"❌ Значение должно быть от 0 до {MAX_OWNER_PAUSE_MINUTES} минут.",
                saved=False,
            )
        await repo.settings.set("owner_pause_minutes", str(value))
        return EditOutcome(
            f"✅ Пауза при активности владельца: `{value}` мин.",
            parse_mode="Markdown",
        )

    return validate


@router.message(AdminStates.waiting_for_owner_pause, F.chat.type == "private")
async def save_owner_pause(message: Message, repo: BotRepository, state: FSMContext) -> None:
    if not await verify_admin(message, repo):
        return
    await finalize_setting_edit(
        message,
        state,
        validator=_make_owner_pause_validator(repo),
        fallback_keyboard=get_back_to_behavior_keyboard(),
    )


# -- Stop / resume hotwords ----------------------------------------------------

def _make_hotword_editor(
    callback_data: str,
    fsm_state: AdminStates,
    *,
    title: str,
    description: str,
    setting_key: str,
):
    """Factory that wires up a stop/resume word edit screen."""

    @router.callback_query(F.data == callback_data)
    async def _start(callback: CallbackQuery, repo: BotRepository, state: FSMContext) -> None:
        current = await repo.settings.get(setting_key, "")
        await _start_edit(
            callback,
            state,
            fsm_state=fsm_state,
            text=(
                f"{title}\n\n"
                f"Текущее значение: `{current or 'не задано'}`\n\n"
                f"{description}\n"
                "Чтобы очистить, отправь `-`."
            ),
        )

    def _validator(repo: BotRepository):
        async def validate(raw: str) -> EditOutcome:
            value = "" if raw == "-" else raw.strip()
            if len(value) > 64:
                return EditOutcome("❌ Слишком длинно. Максимум 64 символа.", saved=False)
            await repo.settings.set(setting_key, value)
            return EditOutcome(
                f"✅ Сохранено: `{value or 'пусто'}`",
                parse_mode="Markdown",
            )

        return validate

    @router.message(fsm_state, F.chat.type == "private")
    async def _save(message: Message, repo: BotRepository, state: FSMContext) -> None:
        if not await verify_admin(message, repo):
            return
        await finalize_setting_edit(
            message,
            state,
            validator=_validator(repo),
            fallback_keyboard=get_back_to_behavior_keyboard(),
        )


_make_hotword_editor(
    callback_data="behavior_stop_word",
    fsm_state=AdminStates.waiting_for_stop_word,
    title="🛑 **Стоп-слово**",
    description=(
        "Отправь короткую фразу. Если ты сам напишешь её в любом чате, "
        "бот сразу замолкает в этом чате до отмены."
    ),
    setting_key="stop_word",
)

_make_hotword_editor(
    callback_data="behavior_resume_word",
    fsm_state=AdminStates.waiting_for_resume_word,
    title="▶️ **Старт-слово**",
    description=(
        "Отправь короткую фразу. Если ты сам напишешь её в чате, бот снова "
        "начинает отвечать (снимает паузу)."
    ),
    setting_key="resume_word",
)


# -- Toxicity filter -----------------------------------------------------------

@router.callback_query(F.data == "behavior_toggle_toxicity")
async def toggle_toxicity(callback: CallbackQuery, repo: BotRepository) -> None:
    """Toggle the simple keyword-based toxicity filter."""
    current = await repo.settings.get("toxicity_filter_enabled", "1")
    new_state = "0" if current == "1" else "1"
    await repo.settings.set("toxicity_filter_enabled", new_state)
    status = "включён" if new_state == "1" else "выключен"
    await _render_behavior_settings(callback, repo, answer_text=f"Фильтр токсичности {status}")


@router.callback_query(F.data == "behavior_toxicity_words")
async def start_toxicity_words_edit(
    callback: CallbackQuery, repo: BotRepository, state: FSMContext
) -> None:
    current = await repo.settings.get("toxicity_keywords", "")
    await _start_edit(
        callback,
        state,
        fsm_state=AdminStates.waiting_for_toxicity_words,
        text=(
            "📜 **Слова-маркеры токсичности**\n\n"
            f"Текущий список: `{current or 'используется встроенный'}`\n\n"
            "Отправь свои слова через запятую. Если сообщение содержит "
            "любое из них, бот не отвечает.\n"
            "Чтобы вернуть встроенный набор по умолчанию, отправь `-`."
        ),
    )


def _make_toxicity_words_validator(repo: BotRepository):
    async def validate(raw: str) -> EditOutcome:
        if raw == "-":
            await repo.settings.set("toxicity_keywords", "")
            return EditOutcome("✅ Возвращён встроенный список токсичности.")
        normalized = ",".join(
            dict.fromkeys(
                word.strip().lower()
                for word in raw.split(",")
                if word.strip()
            )
        )
        await repo.settings.set("toxicity_keywords", normalized)
        return EditOutcome(
            f"✅ Список сохранён: `{normalized or 'пусто'}`",
            parse_mode="Markdown",
        )

    return validate


@router.message(AdminStates.waiting_for_toxicity_words, F.chat.type == "private")
async def save_toxicity_words(
    message: Message, repo: BotRepository, state: FSMContext
) -> None:
    if not await verify_admin(message, repo):
        return
    await finalize_setting_edit(
        message,
        state,
        validator=_make_toxicity_words_validator(repo),
        fallback_keyboard=get_back_to_behavior_keyboard(),
    )
