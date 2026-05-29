"""Filesystem helpers for the Telethon session file."""

from pathlib import Path

SESSION_NAME = "telegram_account"


def session_paths() -> tuple[Path, Path]:
    """Return the local files created by the Telegram account session."""
    return Path(f"{SESSION_NAME}.session"), Path(f"{SESSION_NAME}.session-journal")
