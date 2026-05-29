"""AI provider integration package.

The package separates concerns that used to live in the single ``services/ai.py``:

* ``config``    — provider-agnostic ``AIConfig`` resolution from settings.
* ``providers`` — abstract base class and per-vendor implementations.
* ``registry``  — caching factory that returns a configured provider.
* ``models``    — model listing utilities (used by the admin UI).
* ``reply``     — high-level convenience helper used by Business handlers.
"""

from services.ai.config import (
    AI_PROVIDER_LABELS,
    AI_PROVIDERS,
    AIConfig,
    get_ai_config,
)
from services.ai.models import list_available_models
from services.ai.providers.base import AIProvider
from services.ai.registry import get_ai_provider
from services.ai.reply import generate_reply

__all__ = (
    "AIConfig",
    "AIProvider",
    "AI_PROVIDERS",
    "AI_PROVIDER_LABELS",
    "get_ai_config",
    "get_ai_provider",
    "list_available_models",
    "generate_reply",
)
