"""Reusable helpers for FSM-driven setting editors in the admin panel.

Most admin screens follow the same flow: open an edit prompt, switch to a
``waiting_for_*`` state with ``menu_message_id`` saved in FSM data, receive a
text message, validate it, and edit the original menu message with the result.
This module factors that pattern into a small set of helpers so each screen
only declares its labels and validators.
"""

from dataclasses import dataclass
from typing import Awaitable, Callable

from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message

from handlers.admin.ui import bot_edit_text_safe


@dataclass(slots=True)
class EditOutcome:
    """Result of validating a value typed by the admin."""

    text: str
    parse_mode: str | None = None
    saved: bool = True


# A validator returns either an ``EditOutcome`` or a tuple ``(text, parse_mode)``
# describing the edit message; ``saved=False`` keeps the FSM state and lets the
# admin try again, ``saved=True`` clears the state.
Validator = Callable[[str], Awaitable[EditOutcome] | EditOutcome]


async def finalize_setting_edit(
    message: Message,
    state: FSMContext,
    *,
    validator: Validator,
    fallback_keyboard: InlineKeyboardMarkup,
    expired_text: str = "❌ Сессия настройки истекла.",
    delete_input_label: str = "input",
) -> None:
    """Run the boilerplate around a single FSM-driven setting edit.

    The caller passes a ``validator`` that does the actual saving and returns
    the message to render. Successful edits clear the FSM state; validation
    failures keep it so the admin can retry without reopening the screen.
    """
    raw_value = (message.text or "").strip()

    try:
        await message.delete()
    except Exception:
        # Best-effort: failing to delete an input message must not block the flow.
        pass

    data = await state.get_data()
    menu_message_id = data.get("menu_message_id")
    if not menu_message_id:
        await state.clear()
        await message.answer(expired_text, reply_markup=fallback_keyboard)
        return

    result = validator(raw_value)
    outcome = await result if hasattr(result, "__await__") else result

    if outcome.saved:
        await state.clear()

    await bot_edit_text_safe(
        message.bot,
        chat_id=message.chat.id,
        message_id=menu_message_id,
        text=outcome.text,
        reply_markup=fallback_keyboard,
        parse_mode=outcome.parse_mode,
    )
