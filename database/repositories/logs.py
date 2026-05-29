"""CRUD for conversation logs and aggregate statistics."""

from typing import Any

from database.db import DatabaseManager


class LogRepository:
    """Handles system logs auditing, interaction logging, and statistics."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def log_interaction(
        self,
        connection_id: str,
        chat_id: int,
        sender_id: int,
        message_text: str,
        reply_text: str | None = None,
    ) -> None:
        """Log a business chat message and the bot's reply."""
        await self.db.execute(
            """
            INSERT INTO conversation_logs (connection_id, chat_id, sender_id, message_text, reply_text)
            VALUES (?, ?, ?, ?, ?);
            """,
            (connection_id, chat_id, sender_id, message_text, reply_text),
        )

    async def get_stats(self) -> dict[str, Any]:
        """Gather usage statistics for the admin dashboard."""
        total_messages_row = await self.db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM conversation_logs;"
        )
        total_replies_row = await self.db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM conversation_logs WHERE reply_text IS NOT NULL;"
        )
        active_chats_row = await self.db.fetch_one(
            "SELECT COUNT(DISTINCT chat_id) AS cnt FROM conversation_logs;"
        )
        blacklisted_row = await self.db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM blacklist;"
        )

        return {
            "total_messages_processed": (total_messages_row or {}).get("cnt", 0),
            "total_replies_sent": (total_replies_row or {}).get("cnt", 0),
            "active_chats_count": (active_chats_row or {}).get("cnt", 0),
            "blacklisted_count": (blacklisted_row or {}).get("cnt", 0),
        }

    async def get_recent(self, limit: int = 5) -> list[dict]:
        """Return recent communication logs for auditing."""
        return await self.db.fetch_all(
            """
            SELECT * FROM conversation_logs
            ORDER BY timestamp DESC
            LIMIT ?;
            """,
            (limit,),
        )

    async def get_chat_history(self, chat_id: int, limit: int = 5) -> list[dict]:
        """Return the most recent interactions for a chat in chronological order.

        Used to build short conversation context for AI replies. Only entries
        that produced a reply are returned, so the model sees real exchanges.
        """
        rows = await self.db.fetch_all(
            """
            SELECT message_text, reply_text
            FROM conversation_logs
            WHERE chat_id = ? AND reply_text IS NOT NULL
            ORDER BY id DESC
            LIMIT ?;
            """,
            (chat_id, limit),
        )
        return list(reversed(rows))
