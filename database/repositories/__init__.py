"""Database repositories grouped by aggregate.

Each module owns CRUD for a single domain table and is meant to be used through
``BotRepository`` exposed attributes (``repo.connections``, ``repo.settings``,
``repo.blacklist``, ``repo.logs``, ``repo.archive``).
"""

from database.repositories.blacklist import BlacklistRepository
from database.repositories.chat_notes import ChatNotesRepository
from database.repositories.chat_state import ChatStateRepository
from database.repositories.connections import ConnectionRepository
from database.repositories.logs import LogRepository
from database.repositories.messages_archive import MessageArchiveRepository
from database.repositories.settings import SettingsRepository

__all__ = (
    "BlacklistRepository",
    "ChatNotesRepository",
    "ChatStateRepository",
    "ConnectionRepository",
    "LogRepository",
    "MessageArchiveRepository",
    "SettingsRepository",
)
