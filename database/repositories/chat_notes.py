"""CRUD for per-chat memory notes used to enrich AI replies."""

from database.db import DatabaseManager


class ChatNotesRepository:
    """Free-form notes about a specific Telegram chat (contact)."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def get(self, chat_id: int) -> str:
        """Return the notes for ``chat_id`` or an empty string."""
        row = await self.db.fetch_one(
            "SELECT notes FROM chat_notes WHERE chat_id = ?;",
            (chat_id,),
        )
        return (row or {}).get("notes") or ""

    async def set(self, chat_id: int, notes: str) -> None:
        """Insert or replace the notes for ``chat_id``."""
        await self.db.execute(
            """
            INSERT INTO chat_notes (chat_id, notes)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (chat_id, notes),
        )

    async def delete(self, chat_id: int) -> None:
        """Remove notes for ``chat_id`` if present."""
        await self.db.execute(
            "DELETE FROM chat_notes WHERE chat_id = ?;",
            (chat_id,),
        )

    async def list_recent(self, limit: int = 20) -> list[dict]:
        """Return recently updated notes for the admin panel."""
        return await self.db.fetch_all(
            """
            SELECT chat_id, notes, updated_at
            FROM chat_notes
            WHERE notes <> ''
            ORDER BY updated_at DESC
            LIMIT ?;
            """,
            (limit,),
        )
