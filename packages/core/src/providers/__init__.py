"""LLM Provider implementations for The Daily Clearing.

This module provides a unified interface for different LLM providers:
- OpenRouter (default): Access to DeepSeek, Claude, and other models via unified API
- Anthropic (fallback): Direct access to Claude models

Usage:
    from src.providers import get_provider, ProviderType

    # Get default provider (OpenRouter)
    provider = get_provider()

    # Get specific provider
    anthropic_provider = get_provider(ProviderType.ANTHROPIC)

    # Get tier-specific providers
    tier1_provider = get_tier1_provider()  # DeepSeek for fast/cheap tasks
    tier2_provider = get_tier2_provider()  # DeepSeek or Claude for reasoning
"""

from .base import (
    BaseLLMProvider,
    LLMResponse,
    ProviderError,
    RateLimitError,
    AuthenticationError,
    ModelNotFoundError,
)
from .openrouter import OpenRouterProvider
from .anthropic import AnthropicProvider
from .factory import (
    ProviderType,
    get_provider,
    get_tier1_provider,
    get_tier2_provider,
    create_provider,
)

__all__ = [
    # Base classes
    "BaseLLMProvider",
    "LLMResponse",
    "ProviderError",
    "RateLimitError",
    "AuthenticationError",
    "ModelNotFoundError",
    # Providers
    "OpenRouterProvider",
    "AnthropicProvider",
    # Factory
    "ProviderType",
    "get_provider",
    "get_tier1_provider",
    "get_tier2_provider",
    "create_provider",
]
