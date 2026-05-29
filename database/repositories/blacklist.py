"""CRUD for the chat/user blacklist."""

from database.db import DatabaseManager


class BlacklistRepository:
    """Handles chat/user blacklist CRUD operations."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def add(self, chat_id: int, username: str | None = None, reason: str | None = None) -> None:
        """Add a chat/user ID to the blacklist."""
        await self.db.execute(
            """
            INSERT INTO blacklist (chat_id, username, reason)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                username = COALESCE(excluded.username, blacklist.username),
                reason = COALESCE(excluded.reason, blacklist.reason);
            """,
            (chat_id, username, reason),
        )

    async def remove(self, chat_id: int) -> bool:
        """Remove a chat/user ID. Returns True if a row was deleted."""
        affected = await self.db.execute(
            "DELETE FROM blacklist WHERE chat_id = ?;", (chat_id,)
        )
        return affected > 0

    async def contains(self, chat_id: int) -> bool:
        """Return whether a chat/user ID is blacklisted."""
        row = await self.db.fetch_one(
            "SELECT 1 AS present FROM blacklist WHERE chat_id = ? LIMIT 1;", (chat_id,)
        )
        return row is not None

    async def all(self) -> list[dict]:
        """Return the full blacklist sorted by recency."""
        return await self.db.fetch_all(
            "SELECT * FROM blacklist ORDER BY created_at DESC;"
        )
