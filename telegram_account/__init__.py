"""Telethon account integration package.

The package replaces the previous monolithic ``telegram_account.py`` and
splits responsibilities by concern:

* ``client``    — singleton client lifecycle (init, get, reset).
* ``session``   — local session file paths and cleanup helpers.
* ``view_once`` — incoming view-once media interceptor.
* ``media``     — small Telethon media inspection helpers.
"""

from telegram_account.client import (
    SESSION_NAME,
    get_client,
    get_existing_client,
    init_client,
    reset_client_session,
)

__all__ = (
    "SESSION_NAME",
    "init_client",
    "get_client",
    "get_existing_client",
    "reset_client_session",
)
