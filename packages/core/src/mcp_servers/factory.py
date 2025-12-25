"""Factory functions for creating MCP servers.

This module provides a wrapper around the provider factory to create
LLM providers using the OpenRouter → Anthropic fallback strategy.
"""

from typing import Dict
from .base_provider import BaseLLMProvider
from ..providers.factory import get_tier1_provider, get_tier2_provider


def create_claude_haiku_server(api_key: str = None) -> BaseLLMProvider:
    """
    Create Tier 1 provider (uses OpenRouter DeepSeek by default, falls back to Claude Haiku).

    Args:
        api_key: Optional API key (provider factory handles loading from secrets)

    Returns:
        BaseLLMProvider configured for Tier 1 (fast/cheap inference)
    """
    # Provider factory handles OpenRouter → Anthropic fallback automatically
    return get_tier1_provider()


def create_claude_sonnet_server(api_key: str = None) -> BaseLLMProvider:
    """
    Create Tier 2 provider (uses OpenRouter DeepSeek by default, falls back to Claude Sonnet).

    Args:
        api_key: Optional API key (provider factory handles loading from secrets)

    Returns:
        BaseLLMProvider configured for Tier 2 (smart/capable inference)
    """
    # Provider factory handles OpenRouter → Anthropic fallback automatically
    return get_tier2_provider()


def create_mcp_servers() -> Dict[str, BaseLLMProvider]:
    """
    Create all MCP servers for the system.

    Uses provider factory which automatically handles:
    - OpenRouter as primary provider (cost-effective)
    - Anthropic as fallback provider (if OpenRouter unavailable)

    Returns:
        Dictionary mapping server names to MCP server instances
    """
    return {
        "tier1": get_tier1_provider(),
        "tier2": get_tier2_provider(),
    }


def get_tier1_server() -> BaseLLMProvider:
    """
    Get Tier 1 provider (fast/cheap inference for simple tasks).

    Uses OpenRouter DeepSeek by default, falls back to Claude Haiku if unavailable.

    Returns:
        BaseLLMProvider for Tier 1 agents
    """
    return get_tier1_provider()


def get_tier2_server() -> BaseLLMProvider:
    """
    Get Tier 2 provider (smart/capable inference for complex reasoning).

    Uses OpenRouter DeepSeek by default, falls back to Claude Sonnet if unavailable.

    Returns:
        BaseLLMProvider for Tier 2 agents
    """
    return get_tier2_provider()
