"""
Tests for the base LLM provider interface.
"""

import pytest
from dataclasses import dataclass
from typing import Optional

from src.providers.base import (
    BaseLLMProvider,
    LLMResponse,
    ModelInfo,
    ProviderStats,
    Message,
    ModelTier,
    ProviderError,
    RateLimitError,
    AuthenticationError,
)


# ============================================================================
# LLMResponse Tests
# ============================================================================


class TestLLMResponse:
    """Tests for the LLMResponse dataclass."""

    def test_create_response(self):
        """Test creating an LLM response."""
        response = LLMResponse(
            content="Test response",
            model="test-model",
            provider="test-provider",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            response_time_seconds=1.5,
            finish_reason="stop",
        )
        assert response.content == "Test response"
        assert response.model == "test-model"
        assert response.provider == "test-provider"
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.total_tokens == 150  # property
        assert response.cost_usd == 0.001
        assert response.finish_reason == "stop"

    def test_response_with_defaults(self):
        """Test response with default values."""
        response = LLMResponse(
            content="Test",
            model="model",
            provider="provider",
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            response_time_seconds=0.5,
        )
        assert response.finish_reason == "stop"
        assert response.metadata == {}
        assert response.total_tokens == 0

    def test_response_to_dict(self):
        """Test response to_dict method."""
        response = LLMResponse(
            content="Test",
            model="model",
            provider="provider",
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.001,
            response_time_seconds=1.0,
        )
        d = response.to_dict()
        assert d["content"] == "Test"
        assert d["model"] == "model"
        assert d["total_tokens"] == 15
        assert "created_at" in d

    @pytest.mark.parametrize(
        "input_tokens,output_tokens,expected_total",
        [
            (0, 0, 0),
            (100, 50, 150),
            (1000, 500, 1500),
            (10000, 5000, 15000),
        ],
    )
    def test_token_counting(self, input_tokens, output_tokens, expected_total):
        """Test token counting in responses."""
        response = LLMResponse(
            content="Test",
            model="model",
            provider="provider",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,
            response_time_seconds=1.0,
        )
        assert response.total_tokens == expected_total

    def test_tokens_per_second(self):
        """Test tokens per second calculation."""
        response = LLMResponse(
            content="Test",
            model="model",
            provider="provider",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            response_time_seconds=2.0,
        )
        assert response.tokens_per_second == 25.0  # 50 / 2.0

    def test_tokens_per_second_zero_time(self):
        """Test tokens per second with zero time."""
        response = LLMResponse(
            content="Test",
            model="model",
            provider="provider",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            response_time_seconds=0.0,
        )
        assert response.tokens_per_second == 0.0


# ============================================================================
# ModelInfo Tests
# ============================================================================


class TestModelInfo:
    """Tests for the ModelInfo dataclass."""

    def test_create_model_info(self):
        """Test creating model info."""
        info = ModelInfo(
            model_id="deepseek/deepseek-v3.2",
            name="DeepSeek V3.2",
            provider="openrouter",
            tier=ModelTier.TIER1,
            context_length=128000,
            input_cost_per_million=0.27,
            output_cost_per_million=1.10,
            supports_vision=False,
            supports_function_calling=True,
        )
        assert info.model_id == "deepseek/deepseek-v3.2"
        assert info.name == "DeepSeek V3.2"
        assert info.provider == "openrouter"
        assert info.tier == ModelTier.TIER1
        assert info.input_cost_per_million == 0.27
        assert info.output_cost_per_million == 1.10
        assert info.context_length == 128000
        assert info.supports_function_calling is True

    def test_model_info_defaults(self):
        """Test model info with default values."""
        info = ModelInfo(
            model_id="test-model",
            name="Test",
            provider="test",
            tier=ModelTier.TIER1,
            context_length=4096,
            input_cost_per_million=0.0,
            output_cost_per_million=0.0,
        )
        assert info.supports_vision is False
        assert info.supports_function_calling is True
        assert info.supports_streaming is True
        assert info.description == ""

    def test_input_cost_per_token(self):
        """Test input cost per token property."""
        info = ModelInfo(
            model_id="test",
            name="Test",
            provider="test",
            tier=ModelTier.TIER1,
            context_length=4096,
            input_cost_per_million=1.0,
            output_cost_per_million=2.0,
        )
        assert info.input_cost_per_token == 1.0 / 1_000_000

    def test_output_cost_per_token(self):
        """Test output cost per token property."""
        info = ModelInfo(
            model_id="test",
            name="Test",
            provider="test",
            tier=ModelTier.TIER1,
            context_length=4096,
            input_cost_per_million=1.0,
            output_cost_per_million=2.0,
        )
        assert info.output_cost_per_token == 2.0 / 1_000_000

    @pytest.mark.parametrize(
        "input_cost,output_cost,input_tokens,output_tokens,expected_cost",
        [
            (1.0, 1.0, 1000000, 1000000, 2.0),
            (0.27, 1.10, 1000000, 1000000, 1.37),
            (3.0, 15.0, 100000, 50000, 1.05),  # 0.3 + 0.75
            (0.0, 0.0, 1000000, 1000000, 0.0),
        ],
    )
    def test_cost_calculation(
        self, input_cost, output_cost, input_tokens, output_tokens, expected_cost
    ):
        """Test cost calculation for different token counts."""
        info = ModelInfo(
            model_id="test",
            name="Test",
            provider="test",
            tier=ModelTier.TIER1,
            context_length=128000,
            input_cost_per_million=input_cost,
            output_cost_per_million=output_cost,
        )
        actual_cost = (
            input_tokens * info.input_cost_per_token
            + output_tokens * info.output_cost_per_token
        )
        assert abs(actual_cost - expected_cost) < 0.01


# ============================================================================
# ProviderStats Tests
# ============================================================================


class TestProviderStats:
    """Tests for the ProviderStats dataclass."""

    def test_create_stats(self):
        """Test creating provider stats."""
        stats = ProviderStats(
            total_requests=100,
            total_input_tokens=100000,
            total_output_tokens=50000,
            total_cost_usd=1.50,
            total_response_time=50.0,
            errors=5,
            rate_limits_hit=2,
        )
        assert stats.total_requests == 100
        assert stats.total_input_tokens == 100000
        assert stats.total_output_tokens == 50000
        assert stats.total_cost_usd == 1.50
        assert stats.errors == 5
        assert stats.rate_limits_hit == 2

    def test_stats_defaults(self):
        """Test stats with default values."""
        stats = ProviderStats()
        assert stats.total_requests == 0
        assert stats.total_input_tokens == 0
        assert stats.total_output_tokens == 0
        assert stats.total_cost_usd == 0.0
        assert stats.errors == 0
        assert stats.rate_limits_hit == 0

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        stats = ProviderStats(
            total_requests=95,
            errors=5,
        )
        # success_rate is (total_requests / (total_requests + errors)) * 100
        assert stats.success_rate == 95.0

    def test_success_rate_no_requests(self):
        """Test success rate with no requests."""
        stats = ProviderStats()
        assert stats.success_rate == 100.0

    def test_average_response_time(self):
        """Test average response time calculation."""
        stats = ProviderStats(
            total_requests=10,
            total_response_time=50.0,
        )
        assert stats.average_response_time == 5.0

    def test_average_response_time_no_requests(self):
        """Test average response time with no requests."""
        stats = ProviderStats()
        assert stats.average_response_time == 0.0

    def test_to_dict(self):
        """Test stats to_dict method."""
        stats = ProviderStats(
            total_requests=10,
            total_input_tokens=1000,
            total_output_tokens=500,
        )
        d = stats.to_dict()
        assert d["total_requests"] == 10
        assert d["total_tokens"] == 1500
        assert "success_rate" in d


# ============================================================================
# Message Tests
# ============================================================================


class TestMessage:
    """Tests for message structures."""

    def test_user_message(self):
        """Test creating a user message."""
        msg = Message(role="user", content="Hello, AI!")
        assert msg.role == "user"
        assert msg.content == "Hello, AI!"

    def test_assistant_message(self):
        """Test creating an assistant message."""
        msg = Message(role="assistant", content="Hello, human!")
        assert msg.role == "assistant"
        assert msg.content == "Hello, human!"

    def test_system_message(self):
        """Test creating a system message."""
        msg = Message(role="system", content="You are a helpful assistant.")
        assert msg.role == "system"
        assert msg.content == "You are a helpful assistant."

    def test_message_with_name(self):
        """Test creating a message with a name."""
        msg = Message(role="user", content="Hello", name="Alice")
        assert msg.name == "Alice"

    @pytest.mark.parametrize(
        "role",
        ["user", "assistant", "system"],
    )
    def test_valid_roles(self, role):
        """Test that various roles are accepted."""
        msg = Message(role=role, content="Test")
        assert msg.role == role

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        msg = Message(role="user", content="Test message")
        d = {"role": msg.role, "content": msg.content}
        assert d == {"role": "user", "content": "Test message"}


# ============================================================================
# BaseLLMProvider Interface Tests
# ============================================================================


class TestBaseLLMProviderInterface:
    """Tests for the base provider interface requirements."""

    def test_interface_has_required_methods(self):
        """Test that the interface defines required methods."""
        assert hasattr(BaseLLMProvider, "complete")
        assert hasattr(BaseLLMProvider, "health_check")
        assert hasattr(BaseLLMProvider, "get_model_info")
        assert hasattr(BaseLLMProvider, "get_stats")
        assert hasattr(BaseLLMProvider, "calculate_cost")

    def test_cannot_instantiate_abstract_class(self):
        """Test that abstract class cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseLLMProvider("api-key", "model")

    def test_concrete_implementation_required(self):
        """Test that concrete implementations must implement abstract methods."""

        class IncompleteProvider(BaseLLMProvider):
            pass

        with pytest.raises(TypeError):
            IncompleteProvider("api-key", "model")


# ============================================================================
# Error Classes Tests
# ============================================================================


class TestProviderErrors:
    """Tests for provider error classes."""

    def test_provider_error(self):
        """Test ProviderError."""
        error = ProviderError("Test error", provider="openrouter")
        assert str(error) == "Test error"
        assert error.provider == "openrouter"

    def test_provider_error_with_details(self):
        """Test ProviderError with details."""
        error = ProviderError(
            "Test error",
            provider="openrouter",
            details={"status_code": 500},
        )
        assert error.details == {"status_code": 500}

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError(
            "Rate limit exceeded",
            provider="openrouter",
            retry_after=60.0,
        )
        assert error.retry_after == 60.0

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Invalid API key", provider="openrouter")
        assert error.provider == "openrouter"


# ============================================================================
# ModelTier Tests
# ============================================================================


class TestModelTier:
    """Tests for ModelTier enum."""

    def test_tier_values(self):
        """Test tier enum values."""
        assert ModelTier.TIER1.value == "tier1"
        assert ModelTier.TIER2.value == "tier2"
        assert ModelTier.TIER3.value == "tier3"
