"""Factory functions for creating MCP servers."""

from typing import Dict
from .base_provider import BaseLLMProvider
from .claude_mcp_server import ClaudeMCPServer
from ..utils.config_loader import load_secrets


def create_claude_haiku_server(api_key: str = None) -> ClaudeMCPServer:
    """
    Create Claude Haiku MCP server (Tier 1).

    Args:
        api_key: Anthropic API key (loads from secrets if None)

    Returns:
        ClaudeMCPServer configured for Haiku
    """
    if api_key is None:
        secrets = load_secrets()
        api_key = secrets["anthropic_api_key"]

    return ClaudeMCPServer(
        api_key=api_key,
        model="claude-3-5-haiku-20241022"
    )


def create_claude_sonnet_server(api_key: str = None) -> ClaudeMCPServer:
    """
    Create Claude Sonnet MCP server (Tier 2).

    Args:
        api_key: Anthropic API key (loads from secrets if None)

    Returns:
        ClaudeMCPServer configured for Sonnet
    """
    if api_key is None:
        secrets = load_secrets()
        api_key = secrets["anthropic_api_key"]

    return ClaudeMCPServer(
        api_key=api_key,
        model="claude-3-5-sonnet-20241022"
    )


def create_mcp_servers() -> Dict[str, BaseLLMProvider]:
    """
    Create all MCP servers for the system.

    Returns:
        Dictionary mapping server names to MCP server instances
    """
    secrets = load_secrets()
    api_key = secrets["anthropic_api_key"]

    return {
        "claude_haiku": create_claude_haiku_server(api_key),
        "claude_sonnet": create_claude_sonnet_server(api_key),
    }


def get_tier1_server() -> ClaudeMCPServer:
    """
    Get Tier 1 MCP server (Haiku for fast execution).

    Returns:
        ClaudeMCPServer for Tier 1 agents
    """
    return create_claude_haiku_server()


def get_tier2_server() -> ClaudeMCPServer:
    """
    Get Tier 2 MCP server (Sonnet for reasoning).

    Returns:
        ClaudeMCPServer for Tier 2 agents
    """
    return create_claude_sonnet_server()
