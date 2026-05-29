import asyncio
import logging
from contextlib import suppress

from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)

_login_tasks: dict[int, asyncio.Task] = {}
_login_locks: dict[int, asyncio.Lock] = {}


async def delete_qr_message(bot, chat_id: int, qr_message_id: int | None) -> None:
    """Delete a QR image message when a login attempt is cancelled or completed."""
    if not qr_message_id:
        return
    try:
        await bot.delete_message(chat_id=chat_id, message_id=qr_message_id)
    except TelegramBadRequest as e:
        logger.debug("Could not delete QR message %s: %s", qr_message_id, e)


async def cancel_login(admin_id: int) -> None:
    """Cancel the active QR login task for an admin, if one exists."""
    task = _login_tasks.pop(admin_id, None)
    if task and not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


def remember_login_task(admin_id: int, task: asyncio.Task) -> None:
    """Store the active QR login task for later cancellation."""
    _login_tasks[admin_id] = task


def forget_login_task_if_current(admin_id: int, task: asyncio.Task | None) -> None:
    """Remove a completed QR login task only if it is still current."""
    if _login_tasks.get(admin_id) is task:
        _login_tasks.pop(admin_id, None)


def get_login_lock(admin_id: int) -> asyncio.Lock:
    """Return a per-admin lock used to serialize login actions."""
    lock = _login_locks.get(admin_id)
    if lock is None:
        lock = asyncio.Lock()
        _login_locks[admin_id] = lock
    return lock
