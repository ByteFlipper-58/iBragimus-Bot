"""PostgreSQL backend built on asyncpg.

asyncpg is imported lazily so the dependency is only required when
``DB_BACKEND=postgres`` is selected.

The repository layer speaks SQL with ``?`` placeholders to stay backend-
agnostic. This module translates them to the ``$N`` form asyncpg expects,
while skipping characters inside single-quoted string literals and ``--``
line comments. Datetime values returned by asyncpg are normalised to
ISO-like strings so callers that slice timestamps keep working.
"""

from __future__ import annotations

import datetime as _dt
import logging
from typing import Any, Sequence, TYPE_CHECKING

from database.backends.base import DatabaseBackend

if TYPE_CHECKING:  # pragma: no cover - typing only
    import asyncpg

logger = logging.getLogger(__name__)


def _translate_placeholders(query: str) -> str:
    """Replace ``?`` with ``$N`` while skipping string literals and comments.

    Handles single-quoted strings (with ``''`` escape), double-quoted
    identifiers (with ``""`` escape), line comments (``--``), and block
    comments (``/* ... */``). Anything outside these is fair game for
    placeholder substitution.
    """
    out: list[str] = []
    i = 0
    n = len(query)
    counter = 0
    while i < n:
        ch = query[i]
        # single-quoted string literal
        if ch == "'":
            out.append(ch)
            i += 1
            while i < n:
                if query[i] == "'":
                    if i + 1 < n and query[i + 1] == "'":
                        out.append("''")
                        i += 2
                        continue
                    out.append("'")
                    i += 1
                    break
                out.append(query[i])
                i += 1
            continue
        # double-quoted identifier
        if ch == '"':
            out.append(ch)
            i += 1
            while i < n:
                if query[i] == '"':
                    if i + 1 < n and query[i + 1] == '"':
                        out.append('""')
                        i += 2
                        continue
                    out.append('"')
                    i += 1
                    break
                out.append(query[i])
                i += 1
            continue
        # line comment
        if ch == "-" and i + 1 < n and query[i + 1] == "-":
            while i < n and query[i] != "\n":
                out.append(query[i])
                i += 1
            continue
        # block comment
        if ch == "/" and i + 1 < n and query[i + 1] == "*":
            out.append("/*")
            i += 2
            while i + 1 < n and not (query[i] == "*" and query[i + 1] == "/"):
                out.append(query[i])
                i += 1
            if i + 1 < n:
                out.append("*/")
                i += 2
            continue
        # placeholder
        if ch == "?":
            counter += 1
            out.append(f"${counter}")
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _normalize_value(value: Any) -> Any:
    """Normalise driver-native types to plain JSON-friendly Python values."""
    if isinstance(value, _dt.datetime):
        # Drop timezone info and microseconds for parity with SQLite's
        # ``CURRENT_TIMESTAMP`` output (``YYYY-MM-DD HH:MM:SS``).
        if value.tzinfo is not None:
            value = value.astimezone(_dt.timezone.utc).replace(tzinfo=None)
        return value.replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, _dt.date):
        return value.strftime("%Y-%m-%d")
    return value


def _record_to_dict(record: "asyncpg.Record | None") -> dict[str, Any] | None:
    if record is None:
        return None
    return {key: _normalize_value(record[key]) for key in record.keys()}


class PostgresBackend(DatabaseBackend):
    """asyncpg-based DAO backend."""

    dialect = "postgres"

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._pool: "asyncpg.pool.Pool | None" = None

    async def connect(self) -> None:
        if self._pool is not None:
            return
        try:
            import asyncpg
        except ImportError as exc:  # pragma: no cover - runtime guard
            raise RuntimeError(
                "asyncpg is required for DB_BACKEND=postgres. "
                "Install it with: pip install asyncpg"
            ) from exc

        self._pool = await asyncpg.create_pool(
            dsn=self.dsn,
            min_size=1,
            max_size=10,
            command_timeout=30,
        )
        logger.info("PostgreSQL pool initialised.")

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL pool closed.")

    async def _ensure_pool(self):
        await self.connect()
        assert self._pool is not None
        return self._pool

    async def initialize_schema(self) -> None:
        from database.migrations.postgres import run_migrations

        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            await run_migrations(conn)

    async def execute(self, query: str, params: Sequence[Any] | None = None) -> int:
        pool = await self._ensure_pool()
        translated = _translate_placeholders(query)
        async with pool.acquire() as conn:
            status = await conn.execute(translated, *(params or ()))
        # asyncpg returns command tags like "INSERT 0 5" / "UPDATE 3" / "DELETE 2".
        try:
            return int(status.split()[-1])
        except (ValueError, IndexError):
            return 0

    async def fetch_one(
        self, query: str, params: Sequence[Any] | None = None
    ) -> dict[str, Any] | None:
        pool = await self._ensure_pool()
        translated = _translate_placeholders(query)
        async with pool.acquire() as conn:
            row = await conn.fetchrow(translated, *(params or ()))
        return _record_to_dict(row)

    async def fetch_all(
        self, query: str, params: Sequence[Any] | None = None
    ) -> list[dict[str, Any]]:
        pool = await self._ensure_pool()
        translated = _translate_placeholders(query)
        async with pool.acquire() as conn:
            rows = await conn.fetch(translated, *(params or ()))
        return [
            {key: _normalize_value(row[key]) for key in row.keys()}
            for row in rows
        ]
