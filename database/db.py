"""Database manager: thin facade over a pluggable backend.

The backend (SQLite or PostgreSQL) is selected by ``settings.DB_BACKEND``.
Repositories receive the manager and call its DAO methods (``execute``,
``fetch_one``, ``fetch_all``) so they stay backend-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

from database.backends import DatabaseBackend, create_backend

logger = logging.getLogger(__name__)


class DatabaseManager:
    """DAO facade. Delegates every call to the active backend."""

    def __init__(self, backend: DatabaseBackend | None = None):
        self._backend = backend or create_backend()

    @property
    def dialect(self) -> str:
        """Active SQL dialect identifier (``sqlite`` / ``postgres``)."""
        return self._backend.dialect

    async def initialize_db(self) -> None:
        """Open the underlying connection and apply pending migrations."""
        logger.info("Initializing database (backend=%s)...", self._backend.dialect)
        await self._backend.connect()
        await self._backend.initialize_schema()
        logger.info("Database initialized successfully.")

    async def close(self) -> None:
        """Close the underlying connection / pool."""
        await self._backend.close()

    async def execute(self, query: str, params: Sequence[Any] | None = None) -> int:
        return await self._backend.execute(query, params)

    async def fetch_one(
        self, query: str, params: Sequence[Any] | None = None
    ) -> dict[str, Any] | None:
        return await self._backend.fetch_one(query, params)

    async def fetch_all(
        self, query: str, params: Sequence[Any] | None = None
    ) -> list[dict[str, Any]]:
        return await self._backend.fetch_all(query, params)
