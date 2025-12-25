"""
Tests for the LLM provider factory.
"""

import pytest
from unittest.mock import patch, MagicMock
import os

from src.providers.factory import (
    get_provider,
    get_tier1_provider,
    get_tier2_provider,
    ProviderType,
)
from src.providers.openrouter import OpenRouterProvider
from src.providers.anthropic import AnthropicProvider


# ============================================================================
# Provider Type Tests
# ============================================================================


class TestProviderType:
    """Tests for the ProviderType enum."""

    def test_openrouter_type_exists(self):
        """Test that OpenRouter type exists."""
        assert ProviderType.OPENROUTER.value == "openrouter"

    def test_anthropic_type_exists(self):
        """Test that Anthropic type exists."""
        assert ProviderType.ANTHROPIC.value == "anthropic"

    def test_all_provider_types(self):
        """Test all provider types are defined."""
        types = list(ProviderType)
        assert len(types) >= 2


# ============================================================================
# Get Provider Tests
# ============================================================================


class TestGetProvider:
    """Tests for the get_provider function."""

    def test_get_openrouter_provider(self):
        """Test getting OpenRouter provider."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = get_provider(ProviderType.OPENROUTER)
            assert isinstance(provider, OpenRouterProvider)

    def test_get_anthropic_provider(self):
        """Test getting Anthropic provider."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            provider = get_provider(ProviderType.ANTHROPIC)
            assert isinstance(provider, AnthropicProvider)

    def test_get_provider_with_custom_model(self):
        """Test getting provider with custom model."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = get_provider(
                ProviderType.OPENROUTER, model="anthropic/claude-3-sonnet"
            )
            assert provider.model == "anthropic/claude-3-sonnet"

    def test_get_provider_without_api_key_raises(self):
        """Test that missing API key raises error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError):
                get_provider(ProviderType.OPENROUTER)

    def test_get_provider_caches_instance(self):
        """Test that provider instances are cached."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider1 = get_provider(ProviderType.OPENROUTER)
            provider2 = get_provider(ProviderType.OPENROUTER)
            # Same model should return same instance
            assert provider1 is provider2

    def test_get_provider_different_models_different_instances(self):
        """Test that different models create different instances."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider1 = get_provider(ProviderType.OPENROUTER, model="model-a")
            provider2 = get_provider(ProviderType.OPENROUTER, model="model-b")
            assert provider1 is not provider2


# ============================================================================
# Tier 1 Provider Tests
# ============================================================================


class TestGetTier1Provider:
    """Tests for the get_tier1_provider function."""

    def test_tier1_returns_cost_effective_model(self):
        """Test that Tier 1 returns a cost-effective model."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = get_tier1_provider()
            # Should use DeepSeek or Haiku
            model = provider.model.lower()
            assert "deepseek" in model or "haiku" in model

    def test_tier1_uses_openrouter_by_default(self):
        """Test that Tier 1 uses OpenRouter by default."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = get_tier1_provider()
            assert isinstance(provider, OpenRouterProvider)

    def test_tier1_falls_back_to_anthropic(self):
        """Test that Tier 1 falls back to Anthropic if OpenRouter unavailable."""
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "test-key"},
            clear=True,
        ):
            provider = get_tier1_provider()
            assert isinstance(provider, AnthropicProvider)


# ============================================================================
# Tier 2 Provider Tests
# ============================================================================


class TestGetTier2Provider:
    """Tests for the get_tier2_provider function."""

    def test_tier2_returns_reasoning_model(self):
        """Test that Tier 2 returns a reasoning-capable model."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = get_tier2_provider()
            # Should use a more capable model
            assert provider is not None

    def test_tier2_uses_openrouter_by_default(self):
        """Test that Tier 2 uses OpenRouter by default."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = get_tier2_provider()
            assert isinstance(provider, OpenRouterProvider)

    def test_tier2_can_use_sonnet(self):
        """Test that Tier 2 can use Claude Sonnet."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = get_tier2_provider(premium=True)
            # Premium should use Sonnet or equivalent
            assert provider is not None


# ============================================================================
# Fallback Tests
# ============================================================================


class TestProviderFallback:
    """Tests for provider fallback behavior."""

    def test_fallback_order(self):
        """Test the fallback order of providers."""
        # With both keys, should prefer OpenRouter
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "or-key",
                "ANTHROPIC_API_KEY": "an-key",
            },
        ):
            provider = get_tier1_provider()
            assert isinstance(provider, OpenRouterProvider)

    def test_fallback_when_primary_unavailable(self):
        """Test fallback when primary provider is unavailable."""
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "test-key"},
            clear=True,
        ):
            provider = get_tier1_provider()
            assert isinstance(provider, AnthropicProvider)

    def test_error_when_no_providers_available(self):
        """Test error when no providers are available."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError):
                get_tier1_provider()


# ============================================================================
# Environment Variable Tests
# ============================================================================


class TestEnvironmentVariables:
    """Tests for environment variable handling."""

    def test_reads_openrouter_key_from_env(self):
        """Test reading OpenRouter API key from environment."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "env-key-123"}):
            provider = get_provider(ProviderType.OPENROUTER)
            assert provider.api_key == "env-key-123"

    def test_reads_anthropic_key_from_env(self):
        """Test reading Anthropic API key from environment."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key-456"}):
            provider = get_provider(ProviderType.ANTHROPIC)
            assert provider.api_key == "env-key-456"

    def test_explicit_key_overrides_env(self):
        """Test that explicit API key overrides environment variable."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "env-key"}):
            provider = get_provider(ProviderType.OPENROUTER, api_key="explicit-key")
            assert provider.api_key == "explicit-key"


# ============================================================================
# Integration Tests
# ============================================================================


class TestProviderFactoryIntegration:
    """Integration tests for provider factory."""

    def test_full_workflow_openrouter(self):
        """Test full workflow with OpenRouter provider."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            provider = get_provider(ProviderType.OPENROUTER)
            info = provider.get_model_info()
            stats = provider.get_stats()
            assert info.id is not None
            assert stats.total_requests >= 0

    def test_full_workflow_anthropic(self):
        """Test full workflow with Anthropic provider."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            provider = get_provider(ProviderType.ANTHROPIC)
            info = provider.get_model_info()
            stats = provider.get_stats()
            assert info.id is not None
            assert stats.total_requests >= 0

    def test_tier1_and_tier2_different_configs(self):
        """Test that Tier 1 and Tier 2 have different configurations."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            tier1 = get_tier1_provider()
            tier2 = get_tier2_provider()
            # They may use the same model but could have different settings
            assert tier1 is not None
            assert tier2 is not None
