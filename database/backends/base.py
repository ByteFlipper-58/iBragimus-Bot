"""Database backend abstraction (DAO interface).

Repositories speak this small DAO API and never touch driver-specific cursors.
Concrete backends (SQLite, PostgreSQL) implement it.

SQL contract:
- All queries use ``?`` as the parameter placeholder. Backends translate to
  their native style if needed.
- Returned rows are plain ``dict[str, Any]`` so callers work the same way
  regardless of backend.
- Timestamp columns are normalised to ``"YYYY-MM-DD HH:MM:SS"`` strings.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence


class DatabaseBackend(ABC):
    """Common DAO API used by every repository."""

    dialect: str = ""

    @abstractmethod
    async def connect(self) -> None:
        """Open underlying resources (connection / pool)."""

    @abstractmethod
    async def close(self) -> None:
        """Release underlying resources."""

    @abstractmethod
    async def initialize_schema(self) -> None:
        """Run pending schema migrations for the active dialect."""

    @abstractmethod
    async def execute(self, query: str, params: Sequence[Any] | None = None) -> int:
        """Run a write query. Returns affected row count when available."""

    @abstractmethod
    async def fetch_one(
        self, query: str, params: Sequence[Any] | None = None
    ) -> dict[str, Any] | None:
        """Run a read query and return the first row or ``None``."""

    @abstractmethod
    async def fetch_all(
        self, query: str, params: Sequence[Any] | None = None
    ) -> list[dict[str, Any]]:
        """Run a read query and return all rows."""
