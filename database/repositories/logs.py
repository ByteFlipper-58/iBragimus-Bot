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
        async with self.db.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO conversation_logs (connection_id, chat_id, sender_id, message_text, reply_text)
                VALUES (?, ?, ?, ?, ?);
                """,
                (connection_id, chat_id, sender_id, message_text, reply_text),
            )
            await conn.commit()

    async def get_stats(self) -> dict[str, Any]:
        """Gather usage statistics for the admin dashboard."""
        async with self.db.get_connection() as conn:
            async with conn.execute("SELECT COUNT(*) as cnt FROM conversation_logs;") as cursor:
                total_messages = (await cursor.fetchone())["cnt"]

            async with conn.execute(
                "SELECT COUNT(*) as cnt FROM conversation_logs WHERE reply_text IS NOT NULL;"
            ) as cursor:
                total_replies = (await cursor.fetchone())["cnt"]

            async with conn.execute(
                "SELECT COUNT(DISTINCT chat_id) as cnt FROM conversation_logs;"
            ) as cursor:
                active_chats = (await cursor.fetchone())["cnt"]

            async with conn.execute("SELECT COUNT(*) as cnt FROM blacklist;") as cursor:
                blacklisted_count = (await cursor.fetchone())["cnt"]

            return {
                "total_messages_processed": total_messages,
                "total_replies_sent": total_replies,
                "active_chats_count": active_chats,
                "blacklisted_count": blacklisted_count,
            }

    async def get_recent(self, limit: int = 5) -> list[dict]:
        """Return recent communication logs for auditing."""
        async with self.db.get_connection() as conn:
            async with conn.execute(
                """
                SELECT * FROM conversation_logs
                ORDER BY timestamp DESC
                LIMIT ?;
                """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_chat_history(self, chat_id: int, limit: int = 5) -> list[dict]:
        """Return the most recent interactions for a chat in chronological order.

        Used to build short conversation context for AI replies. Only entries
        that produced a reply are returned, so the model sees real exchanges.
        """
        async with self.db.get_connection() as conn:
            async with conn.execute(
                """
                SELECT message_text, reply_text
                FROM conversation_logs
                WHERE chat_id = ? AND reply_text IS NOT NULL
                ORDER BY id DESC
                LIMIT ?;
                """,
                (chat_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in reversed(rows)]
