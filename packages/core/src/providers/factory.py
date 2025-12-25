"""Provider factory for creating LLM providers.

This module provides a factory for creating LLM providers with:
- Automatic fallback from OpenRouter to Anthropic
- Tier-specific provider creation (Tier 1 for fast/cheap, Tier 2 for smart)
- Configuration loading from environment/secrets
"""

import os
from enum import Enum
from typing import Any

from .base import BaseLLMProvider, ModelTier, ModelNotFoundError
from .openrouter import OpenRouterProvider, OPENROUTER_MODELS, DEFAULT_TIER1_MODEL, DEFAULT_TIER2_MODEL
from .anthropic import AnthropicProvider, ANTHROPIC_MODELS


class ProviderType(Enum):
    """Available provider types."""

    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"


# Environment variable names for API keys
ENV_OPENROUTER_KEY = "OPENROUTER_API_KEY"
ENV_ANTHROPIC_KEY = "ANTHROPIC_API_KEY"

# Default provider order (try OpenRouter first, then Anthropic)
DEFAULT_PROVIDER_ORDER = [ProviderType.OPENROUTER, ProviderType.ANTHROPIC]


def _load_api_key(provider: ProviderType) -> str | None:
    """
    Load API key for a provider from environment.

    Args:
        provider: Provider type

    Returns:
        API key if found, None otherwise
    """
    if provider == ProviderType.OPENROUTER:
        return os.environ.get(ENV_OPENROUTER_KEY)
    elif provider == ProviderType.ANTHROPIC:
        return os.environ.get(ENV_ANTHROPIC_KEY)
    return None


def _load_api_key_from_secrets(provider: ProviderType) -> str | None:
    """
    Load API key from secrets.json file.

    Args:
        provider: Provider type

    Returns:
        API key if found, None otherwise
    """
    import json
    from pathlib import Path

    # Look for secrets.json in multiple locations
    search_paths = [
        Path("secrets.json"),
        Path("../secrets.json"),
        Path("../../secrets.json"),
        Path.home() / ".clearing" / "secrets.json",
    ]

    for secrets_path in search_paths:
        if secrets_path.exists():
            try:
                with open(secrets_path) as f:
                    secrets = json.load(f)

                if provider == ProviderType.OPENROUTER:
                    return secrets.get("openrouter_api_key")
                elif provider == ProviderType.ANTHROPIC:
                    return secrets.get("anthropic_api_key")
            except (json.JSONDecodeError, IOError):
                continue

    return None


def get_api_key(provider: ProviderType) -> str | None:
    """
    Get API key for a provider, checking environment and secrets file.

    Args:
        provider: Provider type

    Returns:
        API key if found, None otherwise
    """
    # Check environment first
    key = _load_api_key(provider)
    if key:
        return key

    # Fall back to secrets file
    return _load_api_key_from_secrets(provider)


def create_provider(
    provider_type: ProviderType,
    model: str | None = None,
    api_key: str | None = None,
    **kwargs: Any,
) -> BaseLLMProvider:
    """
    Create a specific provider instance.

    Args:
        provider_type: Type of provider to create
        model: Model identifier (uses default if None)
        api_key: API key (loads from environment/secrets if None)
        **kwargs: Additional provider-specific arguments

    Returns:
        Configured provider instance

    Raises:
        ValueError: If API key is not found
        ModelNotFoundError: If model is not available
    """
    # Load API key if not provided
    if not api_key:
        api_key = get_api_key(provider_type)

    if not api_key:
        raise ValueError(
            f"No API key found for {provider_type.value}. "
            f"Set {ENV_OPENROUTER_KEY if provider_type == ProviderType.OPENROUTER else ENV_ANTHROPIC_KEY} "
            "or add to secrets.json"
        )

    if provider_type == ProviderType.OPENROUTER:
        return OpenRouterProvider(
            api_key=api_key,
            model=model or DEFAULT_TIER1_MODEL,
            **kwargs,
        )
    elif provider_type == ProviderType.ANTHROPIC:
        from .anthropic import DEFAULT_TIER1_MODEL as ANTHROPIC_TIER1
        return AnthropicProvider(
            api_key=api_key,
            model=model or ANTHROPIC_TIER1,
            **kwargs,
        )
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


def get_provider(
    provider_type: ProviderType | None = None,
    model: str | None = None,
    fallback: bool = True,
    **kwargs: Any,
) -> BaseLLMProvider:
    """
    Get a provider instance with optional fallback.

    If no provider type is specified, tries providers in order:
    1. OpenRouter (if API key available)
    2. Anthropic (if API key available)

    Args:
        provider_type: Specific provider to use (auto-detect if None)
        model: Model identifier
        fallback: Whether to fall back to other providers if primary fails
        **kwargs: Additional provider arguments

    Returns:
        Configured provider instance

    Raises:
        ValueError: If no provider could be created
    """
    errors = []

    if provider_type:
        # Specific provider requested
        try:
            return create_provider(provider_type, model=model, **kwargs)
        except ValueError as e:
            if not fallback:
                raise
            errors.append(str(e))

    # Try providers in order
    for ptype in DEFAULT_PROVIDER_ORDER:
        if provider_type and ptype == provider_type:
            continue  # Already tried

        try:
            return create_provider(ptype, model=model, **kwargs)
        except ModelNotFoundError:
            # Model from one provider isn't valid for another - try with default
            try:
                return create_provider(ptype, model=None, **kwargs)
            except ValueError as e:
                errors.append(str(e))
                continue
        except ValueError as e:
            errors.append(str(e))
            continue

    raise ValueError(
        f"Could not create any provider. Errors: {'; '.join(errors)}"
    )


def get_tier1_provider(
    provider_type: ProviderType | None = None,
    **kwargs: Any,
) -> BaseLLMProvider:
    """
    Get a Tier 1 (fast/cheap) provider.

    Tier 1 is used for:
    - Search query generation
    - Initial relevance scoring
    - Simple classification tasks

    Default model: DeepSeek Chat (via OpenRouter)

    Args:
        provider_type: Specific provider to use
        **kwargs: Additional provider arguments

    Returns:
        Configured Tier 1 provider
    """
    if provider_type == ProviderType.ANTHROPIC:
        from .anthropic import DEFAULT_TIER1_MODEL as ANTHROPIC_TIER1
        return get_provider(
            provider_type=ProviderType.ANTHROPIC,
            model=ANTHROPIC_TIER1,
            **kwargs,
        )

    return get_provider(
        provider_type=provider_type,
        model=DEFAULT_TIER1_MODEL,
        **kwargs,
    )


def get_tier2_provider(
    provider_type: ProviderType | None = None,
    premium: bool = False,
    **kwargs: Any,
) -> BaseLLMProvider:
    """
    Get a Tier 2 (smart/capable) provider.

    Tier 2 is used for:
    - Quality analysis
    - Bias detection
    - Synthesis and summarization
    - Complex reasoning tasks

    Default model: DeepSeek Chat (via OpenRouter)
    Premium model: Claude Sonnet 4 (via OpenRouter or direct)

    Args:
        provider_type: Specific provider to use
        premium: Use premium Claude model instead of DeepSeek
        **kwargs: Additional provider arguments

    Returns:
        Configured Tier 2 provider
    """
    if premium:
        # Use Claude Sonnet for premium quality
        if provider_type == ProviderType.ANTHROPIC:
            from .anthropic import DEFAULT_TIER2_MODEL as ANTHROPIC_TIER2
            return get_provider(
                provider_type=ProviderType.ANTHROPIC,
                model=ANTHROPIC_TIER2,
                **kwargs,
            )
        else:
            return get_provider(
                provider_type=ProviderType.OPENROUTER,
                model="anthropic/claude-sonnet-4",
                **kwargs,
            )

    if provider_type == ProviderType.ANTHROPIC:
        from .anthropic import DEFAULT_TIER2_MODEL as ANTHROPIC_TIER2
        return get_provider(
            provider_type=ProviderType.ANTHROPIC,
            model=ANTHROPIC_TIER2,
            **kwargs,
        )

    return get_provider(
        provider_type=provider_type,
        model=DEFAULT_TIER2_MODEL,
        **kwargs,
    )


def list_available_models(provider_type: ProviderType | None = None) -> dict[str, dict]:
    """
    List all available models.

    Args:
        provider_type: Filter by provider type

    Returns:
        Dictionary of model_id -> model info
    """
    models = {}

    if provider_type is None or provider_type == ProviderType.OPENROUTER:
        for model_id, info in OPENROUTER_MODELS.items():
            models[model_id] = {
                "name": info.name,
                "provider": "openrouter",
                "tier": info.tier.value,
                "context_length": info.context_length,
                "input_cost": info.input_cost_per_million,
                "output_cost": info.output_cost_per_million,
                "vision": info.supports_vision,
            }

    if provider_type is None or provider_type == ProviderType.ANTHROPIC:
        for model_id, info in ANTHROPIC_MODELS.items():
            models[f"anthropic:{model_id}"] = {
                "name": info.name,
                "provider": "anthropic",
                "tier": info.tier.value,
                "context_length": info.context_length,
                "input_cost": info.input_cost_per_million,
                "output_cost": info.output_cost_per_million,
                "vision": info.supports_vision,
            }

    return models


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    provider_type: ProviderType = ProviderType.OPENROUTER,
    model: str | None = None,
) -> float:
    """
    Estimate cost for a request without making it.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        provider_type: Provider to use for pricing
        model: Model to use for pricing

    Returns:
        Estimated cost in USD
    """
    if provider_type == ProviderType.OPENROUTER:
        model = model or DEFAULT_TIER1_MODEL
        if model in OPENROUTER_MODELS:
            info = OPENROUTER_MODELS[model]
            return (
                input_tokens * info.input_cost_per_token +
                output_tokens * info.output_cost_per_token
            )
    elif provider_type == ProviderType.ANTHROPIC:
        from .anthropic import DEFAULT_TIER1_MODEL as ANTHROPIC_DEFAULT
        model = model or ANTHROPIC_DEFAULT
        if model in ANTHROPIC_MODELS:
            info = ANTHROPIC_MODELS[model]
            return (
                input_tokens * info.input_cost_per_token +
                output_tokens * info.output_cost_per_token
            )

    return 0.0
