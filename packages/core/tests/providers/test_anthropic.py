"""
Tests for the Anthropic LLM provider.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.providers.anthropic import AnthropicProvider


# ============================================================================
# Provider Initialization Tests
# ============================================================================


class TestAnthropicProviderInit:
    """Tests for Anthropic provider initialization."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        provider = AnthropicProvider(api_key="test-key")
        assert provider.api_key == "test-key"

    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        provider = AnthropicProvider(
            api_key="test-key", model="claude-3-opus-20240229"
        )
        assert provider.model == "claude-3-opus-20240229"

    def test_default_model_is_haiku(self):
        """Test that default model is Haiku (cost-effective)."""
        provider = AnthropicProvider(api_key="test-key")
        assert "haiku" in provider.model.lower()

    def test_base_url(self):
        """Test that base URL is correct."""
        provider = AnthropicProvider(api_key="test-key")
        assert provider.base_url == "https://api.anthropic.com"

    @pytest.mark.parametrize(
        "model",
        [
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
            "claude-3-5-sonnet-20241022",
        ],
    )
    def test_init_with_various_models(self, model):
        """Test initialization with various Claude models."""
        provider = AnthropicProvider(api_key="test-key", model=model)
        assert provider.model == model

    def test_init_with_max_retries(self):
        """Test initialization with custom max retries."""
        provider = AnthropicProvider(api_key="test-key", max_retries=5)
        assert provider.max_retries == 5


# ============================================================================
# Headers Tests
# ============================================================================


class TestAnthropicHeaders:
    """Tests for Anthropic request headers."""

    def test_api_key_header(self):
        """Test that API key header is set correctly."""
        provider = AnthropicProvider(api_key="test-key-123")
        headers = provider._get_headers()
        assert headers["x-api-key"] == "test-key-123"

    def test_content_type_header(self):
        """Test that content type header is set."""
        provider = AnthropicProvider(api_key="test-key")
        headers = provider._get_headers()
        assert headers["Content-Type"] == "application/json"

    def test_anthropic_version_header(self):
        """Test that Anthropic version header is set."""
        provider = AnthropicProvider(api_key="test-key")
        headers = provider._get_headers()
        assert "anthropic-version" in headers


# ============================================================================
# Model Info Tests
# ============================================================================


class TestAnthropicModelInfo:
    """Tests for Anthropic model information."""

    def test_get_model_info_haiku(self):
        """Test getting model info for Haiku."""
        provider = AnthropicProvider(
            api_key="test-key", model="claude-3-haiku-20240307"
        )
        info = provider.get_model_info()
        assert "haiku" in info.id.lower()
        assert info.provider == "anthropic"

    def test_get_model_info_sonnet(self):
        """Test getting model info for Sonnet."""
        provider = AnthropicProvider(
            api_key="test-key", model="claude-3-sonnet-20240229"
        )
        info = provider.get_model_info()
        assert "sonnet" in info.id.lower()

    def test_get_model_info_opus(self):
        """Test getting model info for Opus."""
        provider = AnthropicProvider(
            api_key="test-key", model="claude-3-opus-20240229"
        )
        info = provider.get_model_info()
        assert "opus" in info.id.lower()

    def test_model_info_costs(self):
        """Test that model info includes cost information."""
        provider = AnthropicProvider(api_key="test-key")
        info = provider.get_model_info()
        assert info.input_cost_per_million >= 0
        assert info.output_cost_per_million >= 0

    def test_model_info_context_length(self):
        """Test that context length is set."""
        provider = AnthropicProvider(api_key="test-key")
        info = provider.get_model_info()
        assert info.context_length >= 100000  # Claude models have large context


# ============================================================================
# Completion Tests
# ============================================================================


class TestAnthropicComplete:
    """Tests for Anthropic completion method."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance."""
        return AnthropicProvider(api_key="test-key")

    @pytest.fixture
    def mock_response(self):
        """Create a mock API response."""
        return {
            "id": "msg-test-123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "This is a test response."}],
            "model": "claude-3-haiku-20240307",
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

    @pytest.mark.asyncio
    async def test_complete_success(self, provider, mock_response):
        """Test successful completion."""
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            response = await provider.complete("Hello, Claude!")
            assert response.content == "This is a test response."
            assert response.input_tokens == 100
            assert response.output_tokens == 50

    @pytest.mark.asyncio
    async def test_complete_with_system_prompt(self, provider, mock_response):
        """Test completion with system prompt."""
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            response = await provider.complete(
                "Hello!", system_prompt="You are a helpful assistant."
            )
            assert response.content is not None

    @pytest.mark.asyncio
    async def test_complete_with_temperature(self, provider, mock_response):
        """Test completion with temperature setting."""
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            response = await provider.complete("Hello!", temperature=0.5)
            assert response.content is not None

    @pytest.mark.asyncio
    async def test_complete_with_max_tokens(self, provider, mock_response):
        """Test completion with max tokens setting."""
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            response = await provider.complete("Hello!", max_tokens=1000)
            assert response.content is not None

    @pytest.mark.asyncio
    async def test_handles_multiple_content_blocks(self, provider):
        """Test handling of multiple content blocks."""
        mock_response = {
            "id": "msg-test",
            "content": [
                {"type": "text", "text": "First part."},
                {"type": "text", "text": " Second part."},
            ],
            "usage": {"input_tokens": 10, "output_tokens": 10},
        }
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            response = await provider.complete("Hello!")
            assert "First part" in response.content
            assert "Second part" in response.content


# ============================================================================
# JSON Completion Tests
# ============================================================================


class TestAnthropicCompleteJson:
    """Tests for Anthropic JSON completion method."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance."""
        return AnthropicProvider(api_key="test-key")

    @pytest.mark.asyncio
    async def test_complete_json_success(self, provider):
        """Test successful JSON completion."""
        mock_response = {
            "id": "msg-test",
            "content": [{"type": "text", "text": '{"result": "success", "count": 42}'}],
            "usage": {"input_tokens": 50, "output_tokens": 20},
        }
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            result = await provider.complete_json("Return JSON")
            assert result == {"result": "success", "count": 42}

    @pytest.mark.asyncio
    async def test_complete_json_with_schema(self, provider):
        """Test JSON completion with schema."""
        schema = {
            "type": "object",
            "properties": {
                "result": {"type": "string"},
                "count": {"type": "integer"},
            },
        }
        mock_response = {
            "id": "msg-test",
            "content": [{"type": "text", "text": '{"result": "test", "count": 1}'}],
            "usage": {"input_tokens": 50, "output_tokens": 20},
        }
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            result = await provider.complete_json("Return JSON", json_schema=schema)
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_complete_json_handles_markdown(self, provider):
        """Test JSON extraction from markdown code blocks."""
        mock_response = {
            "id": "msg-test",
            "content": [
                {"type": "text", "text": "Here is the JSON:\n```json\n{\"data\": true}\n```"}
            ],
            "usage": {"input_tokens": 50, "output_tokens": 30},
        }
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            result = await provider.complete_json("Return JSON")
            assert result == {"data": True}


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestAnthropicErrorHandling:
    """Tests for Anthropic error handling."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance."""
        return AnthropicProvider(api_key="test-key")

    @pytest.mark.asyncio
    async def test_handles_overloaded_error(self, provider):
        """Test handling of overloaded errors (529)."""
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("Overloaded")
            with pytest.raises(Exception):
                await provider.complete("Hello!")

    @pytest.mark.asyncio
    async def test_handles_rate_limit_error(self, provider):
        """Test handling of rate limit errors."""
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("Rate limited")
            with pytest.raises(Exception):
                await provider.complete("Hello!")

    @pytest.mark.asyncio
    async def test_handles_invalid_api_key(self, provider):
        """Test handling of invalid API key errors."""
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("Invalid API key")
            with pytest.raises(Exception):
                await provider.complete("Hello!")

    @pytest.mark.asyncio
    async def test_handles_empty_response(self, provider):
        """Test handling of empty response."""
        mock_response = {
            "id": "msg-test",
            "content": [],
            "usage": {"input_tokens": 10, "output_tokens": 0},
        }
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            response = await provider.complete("Hello!")
            assert response.content == ""


# ============================================================================
# Statistics Tests
# ============================================================================


class TestAnthropicStats:
    """Tests for Anthropic statistics tracking."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance."""
        return AnthropicProvider(api_key="test-key")

    def test_initial_stats_are_zero(self, provider):
        """Test that initial stats are zero."""
        stats = provider.get_stats()
        assert stats.total_requests == 0

    @pytest.mark.asyncio
    async def test_stats_increment_on_success(self, provider):
        """Test that stats increment on successful requests."""
        mock_response = {
            "id": "msg-test",
            "content": [{"type": "text", "text": "Response"}],
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            await provider.complete("Hello!")
            stats = provider.get_stats()
            assert stats.total_requests == 1
            assert stats.successful_requests == 1


# ============================================================================
# Cost Calculation Tests
# ============================================================================


class TestAnthropicCostCalculation:
    """Tests for cost calculation."""

    @pytest.mark.parametrize(
        "model,expected_input_cost,expected_output_cost",
        [
            ("claude-3-haiku-20240307", 0.25, 1.25),
            ("claude-3-sonnet-20240229", 3.0, 15.0),
            ("claude-3-opus-20240229", 15.0, 75.0),
        ],
    )
    def test_model_pricing(self, model, expected_input_cost, expected_output_cost):
        """Test that model pricing is correct."""
        provider = AnthropicProvider(api_key="test-key", model=model)
        info = provider.get_model_info()
        # Allow some variance in pricing
        assert abs(info.input_cost_per_million - expected_input_cost) < 1.0
        assert abs(info.output_cost_per_million - expected_output_cost) < 5.0
