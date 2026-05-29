"""Cached factory that returns a provider for a given ``AIConfig``.

Providers wrap HTTP clients with their own connection pools, so they are
reused across messages instead of being rebuilt on every reply. The cache key
is the immutable ``AIConfig``; changing provider, model, or API key in the
admin panel naturally produces a new key and a fresh client.
"""

import logging
from typing import Callable

from services.ai.config import AIConfig
from services.ai.providers import AIProvider, AnthropicProvider, GoogleProvider, OpenAIProvider

logger = logging.getLogger(__name__)

_PROVIDER_FACTORIES: dict[str, Callable[[AIConfig], AIProvider]] = {
    "openai": lambda c: OpenAIProvider(c.api_key, c.model_name),
    "anthropic": lambda c: AnthropicProvider(c.api_key, c.model_name),
    "google": lambda c: GoogleProvider(c.api_key, c.model_name),
}

_provider_cache: dict[AIConfig, AIProvider] = {}


def _create_provider(config: AIConfig) -> AIProvider:
    """Instantiate a fresh provider matching ``config.provider``."""
    factory = _PROVIDER_FACTORIES[config.provider]
    provider = factory(config)
    logger.info("AI provider selected from admin settings: %s (%s)", config.provider, config.model_name)
    return provider


def get_ai_provider(config: AIConfig) -> AIProvider:
    """Return a cached AI provider for the given config, creating it on first use."""
    cached = _provider_cache.get(config)
    if cached is not None:
        return cached

    provider = _create_provider(config)
    _provider_cache[config] = provider
    return provider


def clear_provider_cache() -> None:
    """Drop the in-memory cache. Intended for tests and forced reconfiguration."""
    _provider_cache.clear()
