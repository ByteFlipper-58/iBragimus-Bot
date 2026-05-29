"""SQLite backend built on aiosqlite.

Holds a single long-lived connection and serialises access with an asyncio
lock so each ``execute`` / ``commit`` block stays atomic when multiple
updates are processed concurrently.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Sequence

import aiosqlite

from database.backends.base import DatabaseBackend

logger = logging.getLogger(__name__)


def _row_to_dict(row: aiosqlite.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class SQLiteBackend(DatabaseBackend):
    """aiosqlite-based DAO backend."""

    dialect = "sqlite"

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        if self._conn is not None:
            return
        conn = await aiosqlite.connect(self.db_path)
        try:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.execute("PRAGMA journal_mode = WAL;")
        except Exception:
            await conn.close()
            raise
        self._conn = conn

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            logger.info("SQLite connection closed.")

    async def _connection(self) -> aiosqlite.Connection:
        await self.connect()
        assert self._conn is not None
        return self._conn

    async def initialize_schema(self) -> None:
        from database.migrations.sqlite import run_migrations

        async with self._lock:
            conn = await self._connection()
            await run_migrations(conn)

    async def execute(self, query: str, params: Sequence[Any] | None = None) -> int:
        async with self._lock:
            conn = await self._connection()
            cursor = await conn.execute(query, tuple(params or ()))
            await conn.commit()
            return cursor.rowcount

    async def fetch_one(
        self, query: str, params: Sequence[Any] | None = None
    ) -> dict[str, Any] | None:
        async with self._lock:
            conn = await self._connection()
            async with conn.execute(query, tuple(params or ())) as cursor:
                row = await cursor.fetchone()
                return _row_to_dict(row)

    async def fetch_all(
        self, query: str, params: Sequence[Any] | None = None
    ) -> list[dict[str, Any]]:
        async with self._lock:
            conn = await self._connection()
            async with conn.execute(query, tuple(params or ())) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
