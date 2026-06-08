"""SQLite schema migrations.

This is the original migration set, kept verbatim so existing ``data.db``
files keep working without re-initialising.
"""

from __future__ import annotations

import logging

import aiosqlite

logger = logging.getLogger(__name__)

MIGRATIONS: dict[int, list[str]] = {
    1: [
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS business_connections (
            connection_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            is_enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS conversation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connection_id TEXT NOT NULL,
            chat_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            message_text TEXT NOT NULL,
            reply_text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS business_messages (
            message_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            connection_id TEXT NOT NULL,
            sender_id INTEGER NOT NULL,
            sender_name TEXT,
            message_text TEXT NOT NULL,
            media_file_path TEXT,
            media_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (message_id, chat_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS edited_messages_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            old_text TEXT NOT NULL,
            new_text TEXT NOT NULL,
            edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS deleted_messages_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            message_text TEXT NOT NULL,
            deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('ai_enabled', '1');",
        """
        INSERT OR IGNORE INTO settings (key, value) VALUES (
            'system_prompt',
            'Ты отвечаешь в личной переписке Telegram ОТ ИМЕНИ владельца аккаунта, от первого лица. Ты — это он сам. Пиши так, как написал бы живой человек в мессенджере: коротко, по-человечески, без формальностей. Жёсткие правила: 1) Отвечай ОДНИМ сообщением, одним готовым ответом, без вариантов и альтернатив. 2) НИКОГДА не пиши «вот несколько вариантов», «варианты ответа», «можно ответить так», списков с пунктами, тире или маркерами. 3) НИКОГДА не объясняй и не комментируй свой ответ, не давай советов. Только сам ответ. 4) Не используй Markdown, звёздочки, заголовки. Обычный текст, как в чате. 5) Пиши на том же языке, на котором пишет собеседник. 6) Если не знаешь конкретный факт о владельце (время поезда, планы, адрес), не выдумывай — отвечай уклончиво: «уточню», «гляну и скажу», «не помню точно». 7) Длина — обычно 1–2 короткие фразы.'
        );
        """,
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('reply_delay_seconds', '0');",
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('ignored_words', '');",
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('ai_context_enabled', '1');",
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('ai_context_limit', '5');",
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('owner_bio', '');",
        """
        CREATE TABLE IF NOT EXISTS chat_notes (
            chat_id INTEGER PRIMARY KEY,
            notes TEXT NOT NULL DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_state (
            chat_id INTEGER PRIMARY KEY,
            paused_until TIMESTAMP,
            summary TEXT NOT NULL DEFAULT '',
            summary_up_to_id INTEGER NOT NULL DEFAULT 0,
            last_auto_memory_id INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('debounce_seconds', '8');",
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('owner_pause_minutes', '15');",
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('stop_word', '!стоп');",
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('resume_word', '!старт');",
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('toxicity_filter_enabled', '1');",
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('toxicity_keywords', '');",
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_memory_enabled', '1');",
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_memory_every_n', '10');",
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('summary_enabled', '1');",
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('summary_threshold', '30');",
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('owner_style', '');",
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('owner_style_updated_at', '');",
    ],
}


async def get_current_version(conn: aiosqlite.Connection) -> int:
    """Return the current SQLite schema version."""
    try:
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version';"
        ) as cursor:
            if not await cursor.fetchone():
                return 0

        async with conn.execute("SELECT MAX(version) AS max_version FROM schema_version;") as cursor:
            row = await cursor.fetchone()
            if row and row["max_version"] is not None:
                return row["max_version"]
            return 0
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Error checking SQLite schema version: %s", exc)
        return 0


async def run_migrations(conn: aiosqlite.Connection) -> None:
    """Apply pending SQLite schema migrations."""
    current = await get_current_version(conn)
    target = max(MIGRATIONS.keys()) if MIGRATIONS else 0

    if current >= target:
        logger.info("SQLite schema is up-to-date (version %s).", current)
        return

    logger.info("Migrating SQLite schema %s -> %s...", current, target)

    for version in sorted(MIGRATIONS):
        if version <= current:
            continue
        logger.info("Applying SQLite migration %s...", version)
        try:
            for query in MIGRATIONS[version]:
                await conn.execute(query)
            await conn.execute(
                "INSERT INTO schema_version (version) VALUES (?);", (version,)
            )
            await conn.commit()
            logger.info("SQLite migration %s applied.", version)
        except Exception as exc:
            await conn.rollback()
            logger.error("SQLite migration %s failed: %s. Rolled back.", version, exc)
            raise

    logger.info("SQLite migrations complete (version %s).", target)
