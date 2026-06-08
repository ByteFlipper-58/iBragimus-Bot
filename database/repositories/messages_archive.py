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

    async def get_recent_for_chat(self, chat_id: int, limit: int = 12) -> list[dict]:
        """Return the most recent messages for a chat in chronological order.

        Includes both incoming and outgoing messages (the owner's replies are
        archived too), so the AI sees the actual back-and-forth even when some
        incoming messages did not trigger a reply.
        """
        rows = await self.db.fetch_all(
            """
            SELECT message_id, sender_id, sender_name, message_text,
                   media_type, created_at
            FROM business_messages
            WHERE chat_id = ?
              AND message_text IS NOT NULL
              AND message_text <> ''
            ORDER BY created_at DESC, message_id DESC
            LIMIT ?;
            """,
            (chat_id, limit),
        )
        return list(reversed(rows))

    async def get_messages_after(
        self, chat_id: int, after_message_id: int, limit: int = 200
    ) -> list[dict]:
        """Return chronological messages with id > ``after_message_id``."""
        return await self.db.fetch_all(
            """
            SELECT message_id, sender_id, sender_name, message_text, created_at
            FROM business_messages
            WHERE chat_id = ?
              AND message_id > ?
              AND message_text IS NOT NULL
              AND message_text <> ''
            ORDER BY message_id ASC
            LIMIT ?;
            """,
            (chat_id, after_message_id, limit),
        )

    async def count_messages_for_chat(self, chat_id: int) -> int:
        """Total count of archived messages with non-empty text in a chat."""
        row = await self.db.fetch_one(
            """
            SELECT COUNT(*) AS cnt FROM business_messages
            WHERE chat_id = ?
              AND message_text IS NOT NULL
              AND message_text <> '';
            """,
            (chat_id,),
        )
        return int((row or {}).get("cnt") or 0)

    async def get_last_owner_message(
        self, chat_id: int, owner_id: int
    ) -> dict | None:
        """Return the latest message authored by the owner in this chat."""
        return await self.db.fetch_one(
            """
            SELECT message_id, created_at
            FROM business_messages
            WHERE chat_id = ? AND sender_id = ?
            ORDER BY created_at DESC, message_id DESC
            LIMIT 1;
            """,
            (chat_id, owner_id),
        )

    async def get_recent_outgoing_by_owner(
        self, owner_id: int, limit: int = 80
    ) -> list[dict]:
        """Return recent owner-authored messages across all chats, newest first.

        Used by the style-extraction job to mine the owner's writing style.
        """
        return await self.db.fetch_all(
            """
            SELECT message_text, created_at
            FROM business_messages
            WHERE sender_id = ?
              AND message_text IS NOT NULL
              AND message_text <> ''
            ORDER BY created_at DESC, message_id DESC
            LIMIT ?;
            """,
            (owner_id, limit),
        )
