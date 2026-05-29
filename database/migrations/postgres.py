"""PostgreSQL schema migrations.

Mirrors the SQLite schema but uses native types (``BIGINT`` for Telegram
IDs that may exceed 2^31, ``BIGSERIAL`` autoincrement, ``TIMESTAMPTZ`` with
``NOW()``). Upserts already use the standard ``ON CONFLICT (...) DO UPDATE
SET ... excluded.X`` form which works the same way in both engines.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    import asyncpg

logger = logging.getLogger(__name__)

MIGRATIONS: dict[int, list[str]] = {
    1: [
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS business_connections (
            connection_id TEXT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            is_enabled SMALLINT DEFAULT 1,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS blacklist (
            chat_id BIGINT PRIMARY KEY,
            username TEXT,
            reason TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS conversation_logs (
            id BIGSERIAL PRIMARY KEY,
            connection_id TEXT NOT NULL,
            chat_id BIGINT NOT NULL,
            sender_id BIGINT NOT NULL,
            message_text TEXT NOT NULL,
            reply_text TEXT,
            timestamp TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS business_messages (
            message_id BIGINT NOT NULL,
            chat_id BIGINT NOT NULL,
            connection_id TEXT NOT NULL,
            sender_id BIGINT NOT NULL,
            sender_name TEXT,
            message_text TEXT NOT NULL,
            media_file_path TEXT,
            media_type TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (message_id, chat_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS edited_messages_history (
            id BIGSERIAL PRIMARY KEY,
            message_id BIGINT NOT NULL,
            chat_id BIGINT NOT NULL,
            old_text TEXT NOT NULL,
            new_text TEXT NOT NULL,
            edited_at TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS deleted_messages_history (
            id BIGSERIAL PRIMARY KEY,
            message_id BIGINT NOT NULL,
            chat_id BIGINT NOT NULL,
            message_text TEXT NOT NULL,
            deleted_at TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        "INSERT INTO settings (key, value) VALUES ('ai_enabled', '1') ON CONFLICT (key) DO NOTHING;",
        """
        INSERT INTO settings (key, value) VALUES (
            'system_prompt',
            'Ты — умный и вежливый ИИ-ассистент, помогающий отвечать на сообщения в личном профиле Telegram. Отвечай кратко, профессионально и дружелюбно. Если вопрос требует личного участия владельца, вежливо сообщи, что он ответит, как только освободится.'
        ) ON CONFLICT (key) DO NOTHING;
        """,
        "INSERT INTO settings (key, value) VALUES ('reply_delay_seconds', '0') ON CONFLICT (key) DO NOTHING;",
        "INSERT INTO settings (key, value) VALUES ('ignored_words', '') ON CONFLICT (key) DO NOTHING;",
        "INSERT INTO settings (key, value) VALUES ('ai_context_enabled', '1') ON CONFLICT (key) DO NOTHING;",
        "INSERT INTO settings (key, value) VALUES ('ai_context_limit', '5') ON CONFLICT (key) DO NOTHING;",
    ]
}


async def _get_current_version(conn: "asyncpg.Connection") -> int:
    # to_regclass respects the current search_path, so this works regardless
    # of which schema the user provisioned the bot into.
    exists = await conn.fetchval("SELECT to_regclass('schema_version');")
    if not exists:
        return 0
    value = await conn.fetchval("SELECT MAX(version) FROM schema_version;")
    return int(value) if value is not None else 0


async def run_migrations(conn: "asyncpg.Connection") -> None:
    """Apply pending PostgreSQL schema migrations.

    A transaction-scoped advisory lock guards against two processes racing
    to apply the same migration on first launch.
    """
    # Constant advisory lock id specific to this project (arbitrary fixed value).
    _MIGRATION_LOCK_ID = 0x1B7A6_1B07

    async with conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock($1);", _MIGRATION_LOCK_ID)

        current = await _get_current_version(conn)
        target = max(MIGRATIONS.keys()) if MIGRATIONS else 0

        if current >= target:
            logger.info("PostgreSQL schema is up-to-date (version %s).", current)
            return

        logger.info("Migrating PostgreSQL schema %s -> %s...", current, target)

        for version in sorted(MIGRATIONS):
            if version <= current:
                continue
            logger.info("Applying PostgreSQL migration %s...", version)
            for query in MIGRATIONS[version]:
                await conn.execute(query)
            await conn.execute(
                "INSERT INTO schema_version (version) VALUES ($1);", version
            )
            logger.info("PostgreSQL migration %s applied.", version)

        logger.info("PostgreSQL migrations complete (version %s).", target)
