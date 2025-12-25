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
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
            finish_reason="stop",
        )
        assert response.content == "Test response"
        assert response.model == "test-model"
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.total_tokens == 150
        assert response.cost_usd == 0.001
        assert response.finish_reason == "stop"

    def test_response_with_defaults(self):
        """Test response with default values."""
        response = LLMResponse(
            content="Test",
            model="model",
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
        )
        assert response.cost_usd is None
        assert response.finish_reason is None
        assert response.raw_response is None

    def test_response_with_raw_response(self):
        """Test response with raw response data."""
        raw = {"id": "test-123", "choices": []}
        response = LLMResponse(
            content="Test",
            model="model",
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            raw_response=raw,
        )
        assert response.raw_response == raw

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
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=expected_total,
        )
        assert response.total_tokens == expected_total


# ============================================================================
# ModelInfo Tests
# ============================================================================


class TestModelInfo:
    """Tests for the ModelInfo dataclass."""

    def test_create_model_info(self):
        """Test creating model info."""
        info = ModelInfo(
            id="deepseek/deepseek-chat",
            name="DeepSeek Chat",
            provider="openrouter",
            input_cost_per_million=0.27,
            output_cost_per_million=1.10,
            context_length=128000,
            supports_json=True,
            supports_tools=True,
        )
        assert info.id == "deepseek/deepseek-chat"
        assert info.name == "DeepSeek Chat"
        assert info.provider == "openrouter"
        assert info.input_cost_per_million == 0.27
        assert info.output_cost_per_million == 1.10
        assert info.context_length == 128000
        assert info.supports_json is True
        assert info.supports_tools is True

    def test_model_info_defaults(self):
        """Test model info with default values."""
        info = ModelInfo(
            id="test-model",
            name="Test",
            provider="test",
            input_cost_per_million=0.0,
            output_cost_per_million=0.0,
            context_length=4096,
        )
        assert info.supports_json is False
        assert info.supports_tools is False

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
            id="test",
            name="Test",
            provider="test",
            input_cost_per_million=input_cost,
            output_cost_per_million=output_cost,
            context_length=128000,
        )
        actual_cost = (
            input_tokens * info.input_cost_per_million
            + output_tokens * info.output_cost_per_million
        ) / 1_000_000
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
            successful_requests=95,
            failed_requests=5,
            total_input_tokens=100000,
            total_output_tokens=50000,
            total_cost_usd=1.50,
        )
        assert stats.total_requests == 100
        assert stats.successful_requests == 95
        assert stats.failed_requests == 5
        assert stats.total_input_tokens == 100000
        assert stats.total_output_tokens == 50000
        assert stats.total_cost_usd == 1.50

    def test_stats_defaults(self):
        """Test stats with default values."""
        stats = ProviderStats()
        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0
        assert stats.total_input_tokens == 0
        assert stats.total_output_tokens == 0
        assert stats.total_cost_usd == 0.0

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        stats = ProviderStats(
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
        )
        success_rate = (
            stats.successful_requests / stats.total_requests * 100
            if stats.total_requests > 0
            else 0
        )
        assert success_rate == 95.0

    def test_average_tokens_per_request(self):
        """Test average tokens per request calculation."""
        stats = ProviderStats(
            total_requests=100,
            total_input_tokens=100000,
            total_output_tokens=50000,
        )
        avg_input = stats.total_input_tokens / stats.total_requests
        avg_output = stats.total_output_tokens / stats.total_requests
        assert avg_input == 1000
        assert avg_output == 500


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

    @pytest.mark.parametrize(
        "role",
        ["user", "assistant", "system", "tool"],
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
        assert hasattr(BaseLLMProvider, "complete_json")
        assert hasattr(BaseLLMProvider, "get_model_info")
        assert hasattr(BaseLLMProvider, "get_stats")

    def test_cannot_instantiate_abstract_class(self):
        """Test that abstract class cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseLLMProvider()

    def test_concrete_implementation_required(self):
        """Test that concrete implementations must implement abstract methods."""

        class IncompleteProvider(BaseLLMProvider):
            pass

        with pytest.raises(TypeError):
            IncompleteProvider()
