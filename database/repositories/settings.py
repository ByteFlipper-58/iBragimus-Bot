"""CRUD for the key-value settings table."""

from database.db import DatabaseManager


class SettingsRepository:
    """Handles key-value application settings CRUD operations."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def get(self, key: str, default: str | None = None) -> str | None:
        """Return a single setting value by key."""
        async with self.db.get_connection() as conn:
            async with conn.execute(
                "SELECT value FROM settings WHERE key = ?;", (key,)
            ) as cursor:
                row = await cursor.fetchone()
                return row["value"] if row else default

    async def set(self, key: str, value: str) -> None:
        """Insert or update a setting value."""
        async with self.db.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value;
                """,
                (key, value),
            )
            await conn.commit()

    async def all(self) -> dict[str, str]:
        """Return all settings as a dictionary in a single query."""
        async with self.db.get_connection() as conn:
            async with conn.execute("SELECT key, value FROM settings;") as cursor:
                rows = await cursor.fetchall()
                return {row["key"]: row["value"] for row in rows}
