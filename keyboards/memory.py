"""Keyboards for the persona/memory admin screen."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_memory_keyboard() -> InlineKeyboardMarkup:
    """Top-level controls for owner bio and per-contact notes."""
    keyboard = [
        [InlineKeyboardButton(text="🪪 О себе (биография)", callback_data="memory_bio_view")],
        [InlineKeyboardButton(text="✏️ Изменить «о себе»", callback_data="memory_bio_edit")],
        [InlineKeyboardButton(text="📒 Заметки о собеседниках", callback_data="memory_notes_list")],
        [InlineKeyboardButton(text="➕ Добавить заметку по chat_id", callback_data="memory_notes_add")],
        [InlineKeyboardButton(text="🎨 Стиль владельца", callback_data="memory_style_view")],
        [InlineKeyboardButton(text="🔄 Пересобрать стиль", callback_data="memory_style_refresh")],
        [InlineKeyboardButton(text="🧠 Авто-память и сводка", callback_data="memory_auto_view")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_memory_keyboard() -> InlineKeyboardMarkup:
    """One-button keyboard returning to the memory screen."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к памяти", callback_data="memory_menu")]
    ])


def get_chat_note_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Per-note actions: edit / delete / back."""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✏️ Изменить",
                callback_data=f"memory_note_edit:{chat_id}",
            ),
            InlineKeyboardButton(
                text="🗑 Удалить",
                callback_data=f"memory_note_delete:{chat_id}",
            ),
        ],
        [InlineKeyboardButton(text="🔙 К списку заметок", callback_data="memory_notes_list")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_auto_memory_keyboard(
    auto_memory_enabled: bool,
    summary_enabled: bool,
) -> InlineKeyboardMarkup:
    """Toggles for the auto-memory and rolling summary jobs."""
    auto_text = "🟢 Авто-память: вкл" if auto_memory_enabled else "🔴 Авто-память: выкл"
    summary_text = "🟢 Сводка: вкл" if summary_enabled else "🔴 Сводка: выкл"
    keyboard = [
        [InlineKeyboardButton(text=auto_text, callback_data="memory_auto_toggle")],
        [InlineKeyboardButton(text=summary_text, callback_data="memory_summary_toggle")],
        [InlineKeyboardButton(text="🔙 Назад к памяти", callback_data="memory_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
