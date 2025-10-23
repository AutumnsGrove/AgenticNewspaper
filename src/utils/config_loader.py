"""Configuration and secrets loading utilities."""

import json
import os
from pathlib import Path
from typing import Dict, Any
import yaml


def load_secrets() -> Dict[str, str]:
    """
    Load API keys from secrets.json file.

    Returns:
        Dict containing API keys

    Raises:
        FileNotFoundError: If secrets.json doesn't exist
        ValueError: If secrets.json is malformed or missing required keys
    """
    # Get project root directory
    project_root = Path(__file__).parent.parent.parent
    secrets_path = project_root / "secrets.json"

    if not secrets_path.exists():
        raise FileNotFoundError(
            f"secrets.json not found at {secrets_path}. "
            f"Please copy secrets_template.json to secrets.json and add your API keys."
        )

    try:
        with open(secrets_path, 'r') as f:
            secrets = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parsing secrets.json: {e}")

    # Validate required keys
    required_keys = ["anthropic_api_key"]
    missing_keys = [key for key in required_keys if not secrets.get(key)]

    if missing_keys:
        raise ValueError(
            f"Missing required keys in secrets.json: {', '.join(missing_keys)}"
        )

    return secrets


def load_user_preferences() -> Dict[str, Any]:
    """
    Load user preferences from YAML configuration file.

    Returns:
        Dict containing user preferences

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is malformed
    """
    # Get project root directory
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / "config" / "user_preferences.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"user_preferences.yaml not found at {config_path}. "
            f"Please create it from user-preferences-template.yaml"
        )

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing user_preferences.yaml: {e}")

    # Basic validation
    required_sections = ["topics", "sources", "output", "quality", "budget"]
    missing_sections = [
        section for section in required_sections
        if section not in config
    ]

    if missing_sections:
        raise ValueError(
            f"Missing required sections in config: {', '.join(missing_sections)}"
        )

    return config


def get_anthropic_api_key() -> str:
    """
    Get Anthropic API key from secrets.

    Returns:
        Anthropic API key string

    Raises:
        ValueError: If API key is not found or is empty
    """
    secrets = load_secrets()
    api_key = secrets.get("anthropic_api_key", "")

    if not api_key or api_key.startswith("sk-ant-api03-YOUR"):
        raise ValueError(
            "Anthropic API key not configured in secrets.json. "
            "Please add a valid API key."
        )

    return api_key


def get_tavily_api_key() -> str:
    """
    Get Tavily API key from secrets (optional for Phase 1).

    Returns:
        Tavily API key string or empty string if not configured
    """
    secrets = load_secrets()
    return secrets.get("tavily_api_key", "")
