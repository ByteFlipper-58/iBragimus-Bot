"""CRUD for Telegram Business connections."""

from database.db import DatabaseManager


class ConnectionRepository:
    """Handles business connections CRUD operations."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def save(self, connection_id: str, user_id: int, is_enabled: bool = True) -> None:
        """Save or update a business connection."""
        async with self.db.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO business_connections (connection_id, user_id, is_enabled)
                VALUES (?, ?, ?)
                ON CONFLICT(connection_id) DO UPDATE SET is_enabled = excluded.is_enabled;
                """,
                (connection_id, user_id, 1 if is_enabled else 0),
            )
            await conn.commit()

    async def disable(self, connection_id: str) -> None:
        """Mark a business connection as disabled."""
        async with self.db.get_connection() as conn:
            await conn.execute(
                "UPDATE business_connections SET is_enabled = 0 WHERE connection_id = ?;",
                (connection_id,),
            )
            await conn.commit()

    async def get_active(self) -> list[dict]:
        """Return all currently active business connections."""
        async with self.db.get_connection() as conn:
            async with conn.execute(
                "SELECT * FROM business_connections WHERE is_enabled = 1;"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
