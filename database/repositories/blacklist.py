"""CRUD for the chat/user blacklist."""

from database.db import DatabaseManager


class BlacklistRepository:
    """Handles chat/user blacklist CRUD operations."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def add(self, chat_id: int, username: str | None = None, reason: str | None = None) -> None:
        """Add a chat/user ID to the blacklist."""
        async with self.db.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO blacklist (chat_id, username, reason)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    username = COALESCE(excluded.username, username),
                    reason = COALESCE(excluded.reason, reason);
                """,
                (chat_id, username, reason),
            )
            await conn.commit()

    async def remove(self, chat_id: int) -> bool:
        """Remove a chat/user ID. Returns True if a row was deleted."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                "DELETE FROM blacklist WHERE chat_id = ?;", (chat_id,)
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def contains(self, chat_id: int) -> bool:
        """Return whether a chat/user ID is blacklisted."""
        async with self.db.get_connection() as conn:
            async with conn.execute(
                "SELECT 1 FROM blacklist WHERE chat_id = ? LIMIT 1;", (chat_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None

    async def all(self) -> list[dict]:
        """Return the full blacklist sorted by recency."""
        async with self.db.get_connection() as conn:
            async with conn.execute(
                "SELECT * FROM blacklist ORDER BY created_at DESC;"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
