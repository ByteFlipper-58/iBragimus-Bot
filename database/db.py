import asyncio
import logging
from contextlib import asynccontextmanager

import aiosqlite

from config import settings
from database.migrations import run_migrations

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Owns a single long-lived SQLite connection and initializes the schema.

    A shared connection avoids the cost of opening and closing a new connection
    on every query. Access is serialized with an asyncio lock so each
    ``execute``/``commit`` block stays atomic even when multiple updates are
    processed concurrently.
    """

    def __init__(self, db_path: str = settings.DB_PATH):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def _ensure_connection(self) -> aiosqlite.Connection:
        """Open the shared connection on first use and configure pragmas."""
        if self._conn is None:
            conn = await aiosqlite.connect(self.db_path)
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.execute("PRAGMA journal_mode = WAL;")
            self._conn = conn
        return self._conn

    @asynccontextmanager
    async def get_connection(self):
        """Yield the shared SQLite connection while holding the access lock."""
        async with self._lock:
            conn = await self._ensure_connection()
            yield conn

    async def initialize_db(self):
        """Initializes the SQLite database and executes outstanding schema migrations."""
        logger.info("Initializing database...")
        async with self.get_connection() as conn:
            await run_migrations(conn)
        logger.info("Database initialized successfully.")

    async def close(self) -> None:
        """Close the shared SQLite connection during shutdown."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            logger.info("Database connection closed.")
