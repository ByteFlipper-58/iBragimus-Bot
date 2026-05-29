"""Inline keyboard factories for the admin panel.

Each module corresponds to a single admin screen so files stay small and
focused. Importers can keep using ``from keyboards import ...`` thanks to the
re-exports below.
"""

from keyboards.account import (
    get_account_2fa_keyboard,
    get_account_phone_keyboard,
    get_account_qr_keyboard,
    get_account_status_keyboard,
)
from keyboards.ai import (
    get_ai_models_keyboard,
    get_ai_settings_keyboard,
    get_back_to_ai_settings_keyboard,
)
from keyboards.behavior import (
    get_back_to_behavior_keyboard,
    get_behavior_settings_keyboard,
)
from keyboards.blacklist import get_back_to_blacklist_keyboard
from keyboards.common import get_back_keyboard
from keyboards.main import get_main_keyboard

__all__ = (
    "get_main_keyboard",
    "get_back_keyboard",
    "get_ai_settings_keyboard",
    "get_back_to_ai_settings_keyboard",
    "get_ai_models_keyboard",
    "get_behavior_settings_keyboard",
    "get_back_to_behavior_keyboard",
    "get_back_to_blacklist_keyboard",
    "get_account_qr_keyboard",
    "get_account_2fa_keyboard",
    "get_account_phone_keyboard",
    "get_account_status_keyboard",
)
