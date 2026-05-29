"""CRUD for the Business message archive and edit/delete history."""

from database.db import DatabaseManager


class MessageArchiveRepository:
    """Handles business message archiving, edit history, and deletion history."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def save_message(
        self,
        message_id: int,
        chat_id: int,
        connection_id: str,
        sender_id: int,
        sender_name: str | None,
        message_text: str,
        media_file_path: str | None = None,
        media_type: str | None = None,
    ) -> None:
        """Save an incoming or outgoing business message in the archive."""
        await self.db.execute(
            """
            INSERT INTO business_messages (
                message_id, chat_id, connection_id, sender_id,
                sender_name, message_text, media_file_path, media_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(message_id, chat_id) DO UPDATE SET
                message_text = excluded.message_text,
                media_file_path = COALESCE(excluded.media_file_path, business_messages.media_file_path),
                media_type = COALESCE(excluded.media_type, business_messages.media_type);
            """,
            (
                message_id,
                chat_id,
                connection_id,
                sender_id,
                sender_name,
                message_text,
                media_file_path,
                media_type,
            ),
        )

    async def get_message(self, message_id: int, chat_id: int) -> dict | None:
        """Return a single archived message or ``None`` when missing."""
        return await self.db.fetch_one(
            "SELECT * FROM business_messages WHERE message_id = ? AND chat_id = ? LIMIT 1;",
            (message_id, chat_id),
        )

    async def get_messages(self, message_ids: list[int], chat_id: int) -> dict[int, dict]:
        """Return many archived messages for a chat in a single query."""
        if not message_ids:
            return {}

        placeholders = ",".join("?" for _ in message_ids)
        query = (
            f"SELECT * FROM business_messages "
            f"WHERE chat_id = ? AND message_id IN ({placeholders});"
        )
        rows = await self.db.fetch_all(query, (chat_id, *message_ids))
        return {row["message_id"]: row for row in rows}

    async def log_edit(self, message_id: int, chat_id: int, old_text: str, new_text: str) -> None:
        """Log an edit event into the history table."""
        await self.db.execute(
            """
            INSERT INTO edited_messages_history (message_id, chat_id, old_text, new_text)
            VALUES (?, ?, ?, ?);
            """,
            (message_id, chat_id, old_text, new_text),
        )

    async def log_deletion(self, message_id: int, chat_id: int, message_text: str) -> None:
        """Log a deletion event into the history table."""
        await self.db.execute(
            """
            INSERT INTO deleted_messages_history (message_id, chat_id, message_text)
            VALUES (?, ?, ?);
            """,
            (message_id, chat_id, message_text),
        )

    async def get_edit_history(self, message_id: int, chat_id: int) -> list[dict]:
        """Return the full edit history for a message in chronological order."""
        return await self.db.fetch_all(
            """
            SELECT old_text, new_text, edited_at
            FROM edited_messages_history
            WHERE message_id = ? AND chat_id = ?
            ORDER BY edited_at ASC;
            """,
            (message_id, chat_id),
        )
