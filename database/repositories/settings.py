"""CRUD for the key-value settings table."""

from database.db import DatabaseManager


class SettingsRepository:
    """Handles key-value application settings CRUD operations."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def get(self, key: str, default: str | None = None) -> str | None:
        """Return a single setting value by key."""
        row = await self.db.fetch_one(
            "SELECT value FROM settings WHERE key = ?;", (key,)
        )
        return row["value"] if row else default

    async def set(self, key: str, value: str) -> None:
        """Insert or update a setting value."""
        await self.db.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """,
            (key, value),
        )

    async def all(self) -> dict[str, str]:
        """Return all settings as a dictionary in a single query."""
        rows = await self.db.fetch_all("SELECT key, value FROM settings;")
        return {row["key"]: row["value"] for row in rows}
