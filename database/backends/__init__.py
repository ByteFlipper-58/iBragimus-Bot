"""Database backends.

Each backend implements the :class:`DatabaseBackend` DAO interface so
repositories can stay dialect-agnostic. ``create_backend`` picks the right
implementation based on settings.
"""

from database.backends.base import DatabaseBackend


def create_backend() -> DatabaseBackend:
    """Build the configured backend without importing optional drivers eagerly."""
    from config import settings

    backend = settings.DB_BACKEND
    if backend == "sqlite":
        from database.backends.sqlite import SQLiteBackend

        return SQLiteBackend(settings.DB_PATH)
    if backend == "postgres":
        if not settings.DATABASE_URL:
            raise RuntimeError(
                "DB_BACKEND=postgres requires DATABASE_URL to be set "
                "(e.g. postgresql://user:pass@host:5432/dbname)."
            )
        from database.backends.postgres import PostgresBackend

        return PostgresBackend(settings.DATABASE_URL)
    raise ValueError(f"Unsupported DB_BACKEND: {backend!r}")


__all__ = ("DatabaseBackend", "create_backend")
