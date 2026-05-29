"""Aggregate access point for all database repositories.

Instead of a wide facade with hand-written delegation, ``BotRepository`` simply
exposes the per-aggregate repositories as attributes. Callers pick the slice
they need: ``repo.settings.all()``, ``repo.blacklist.add(...)`` and so on.
"""

from database.db import DatabaseManager
from database.repositories import (
    BlacklistRepository,
    ConnectionRepository,
    LogRepository,
    MessageArchiveRepository,
    SettingsRepository,
)


class BotRepository:
    """Thin container that wires per-aggregate repositories together."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.connections = ConnectionRepository(db_manager)
        self.settings = SettingsRepository(db_manager)
        self.blacklist = BlacklistRepository(db_manager)
        self.logs = LogRepository(db_manager)
        self.archive = MessageArchiveRepository(db_manager)
