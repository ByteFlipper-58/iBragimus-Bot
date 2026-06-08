"""Per-chat runtime state: pause window, rolling summary, auto-memory cursor."""

from datetime import datetime, timedelta, timezone

from database.db import DatabaseManager


def _utc_now() -> datetime:
    """Return a naive UTC datetime so values match the SQLite normaliser."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _format_ts(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _parse_ts(raw) -> datetime | None:
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=None) if raw.tzinfo else raw
    text = str(raw).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


class ChatStateRepository:
    """Bookkeeping per ``chat_id`` (pauses, summary, processed message cursor)."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def _get_raw(self, chat_id: int) -> dict | None:
        return await self.db.fetch_one(
            """
            SELECT chat_id, paused_until, summary, summary_up_to_id,
                   last_auto_memory_id, updated_at
            FROM chat_state WHERE chat_id = ?;
            """,
            (chat_id,),
        )

    async def _ensure_row(self, chat_id: int) -> None:
        await self.db.execute(
            """
            INSERT INTO chat_state (chat_id) VALUES (?)
            ON CONFLICT(chat_id) DO NOTHING;
            """,
            (chat_id,),
        )

    async def get_state(self, chat_id: int) -> dict:
        """Return the state row, creating it lazily for a new chat."""
        row = await self._get_raw(chat_id)
        if row is None:
            await self._ensure_row(chat_id)
            row = await self._get_raw(chat_id) or {}
        return {
            "paused_until": _parse_ts(row.get("paused_until")),
            "summary": row.get("summary") or "",
            "summary_up_to_id": int(row.get("summary_up_to_id") or 0),
            "last_auto_memory_id": int(row.get("last_auto_memory_id") or 0),
        }

    async def is_paused(self, chat_id: int) -> bool:
        """True when the chat is muted by an active pause window."""
        row = await self._get_raw(chat_id)
        until = _parse_ts((row or {}).get("paused_until"))
        if until is None:
            return False
        return until > _utc_now()

    async def pause(self, chat_id: int, *, minutes: int | None = None) -> None:
        """Pause auto-replies for ``minutes`` (``None`` means indefinitely)."""
        await self._ensure_row(chat_id)
        if minutes is None:
            # Indefinite pause: store a date far in the future.
            until = _utc_now() + timedelta(days=365 * 50)
        else:
            until = _utc_now() + timedelta(minutes=max(0, minutes))
        await self.db.execute(
            """
            UPDATE chat_state
            SET paused_until = ?, updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = ?;
            """,
            (_format_ts(until), chat_id),
        )

    async def resume(self, chat_id: int) -> None:
        """Clear any active pause for ``chat_id``."""
        await self._ensure_row(chat_id)
        await self.db.execute(
            """
            UPDATE chat_state
            SET paused_until = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = ?;
            """,
            (chat_id,),
        )

    async def set_summary(
        self,
        chat_id: int,
        summary: str,
        up_to_message_id: int,
    ) -> None:
        """Persist a refreshed rolling summary and the cursor it covers."""
        await self._ensure_row(chat_id)
        await self.db.execute(
            """
            UPDATE chat_state
            SET summary = ?, summary_up_to_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = ?;
            """,
            (summary or "", int(up_to_message_id), chat_id),
        )

    async def set_last_auto_memory_id(self, chat_id: int, message_id: int) -> None:
        """Mark the highest archived message processed by the auto-memory job."""
        await self._ensure_row(chat_id)
        await self.db.execute(
            """
            UPDATE chat_state
            SET last_auto_memory_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = ?;
            """,
            (int(message_id), chat_id),
        )
