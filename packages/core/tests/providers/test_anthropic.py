"""
Tests for the Anthropic LLM provider.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import httpx

from src.providers.anthropic import AnthropicProvider, ANTHROPIC_MODELS
from src.providers.base import ModelNotFoundError, LLMResponse, ProviderStats


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
            api_key="test-key", model="claude-sonnet-4-20250514"
        )
        assert provider.model == "claude-sonnet-4-20250514"

    def test_default_model_is_haiku(self):
        """Test that default model is a Haiku variant."""
        provider = AnthropicProvider(api_key="test-key")
        assert "haiku" in provider.model.lower()

    def test_base_url(self):
        """Test that base URL is correct."""
        assert AnthropicProvider.BASE_URL == "https://api.anthropic.com/v1"

    @pytest.mark.parametrize(
        "model",
        list(ANTHROPIC_MODELS.keys()),
    )
    def test_init_with_valid_models(self, model):
        """Test initialization with valid Claude models."""
        provider = AnthropicProvider(api_key="test-key", model=model)
        assert provider.model == model

    def test_init_with_invalid_model(self):
        """Test initialization with invalid model raises error."""
        with pytest.raises(ModelNotFoundError):
            AnthropicProvider(api_key="test-key", model="invalid-model")

    def test_init_with_timeout(self):
        """Test initialization with custom timeout."""
        provider = AnthropicProvider(api_key="test-key", timeout=60.0)
        assert provider.timeout == 60.0


# ============================================================================
# Headers Tests
# ============================================================================


class TestAnthropicHeaders:
    """Tests for Anthropic request headers."""

    def test_api_key_header(self):
        """Test that API key header is set correctly."""
        provider = AnthropicProvider(api_key="test-key-123")
        headers = provider._build_headers()
        assert headers["x-api-key"] == "test-key-123"

    def test_content_type_header(self):
        """Test that content type header is set."""
        provider = AnthropicProvider(api_key="test-key")
        headers = provider._build_headers()
        assert headers["Content-Type"] == "application/json"

    def test_anthropic_version_header(self):
        """Test that Anthropic version header is set."""
        provider = AnthropicProvider(api_key="test-key")
        headers = provider._build_headers()
        assert "anthropic-version" in headers


# ============================================================================
# Model Info Tests
# ============================================================================


class TestAnthropicModelInfo:
    """Tests for Anthropic model information."""

    def test_get_model_info_haiku(self):
        """Test getting model info for Haiku."""
        provider = AnthropicProvider(
            api_key="test-key", model="claude-haiku-4-20250514"
        )
        info = provider.get_model_info()
        assert "haiku" in info.model_id.lower()  # Uses model_id, not id
        assert info.provider == "anthropic"

    def test_get_model_info_sonnet(self):
        """Test getting model info for Sonnet."""
        provider = AnthropicProvider(
            api_key="test-key", model="claude-sonnet-4-20250514"
        )
        info = provider.get_model_info()
        assert "sonnet" in info.model_id.lower()

    def test_get_model_info_opus(self):
        """Test getting model info for Opus."""
        provider = AnthropicProvider(
            api_key="test-key", model="claude-opus-4-20250514"
        )
        info = provider.get_model_info()
        assert "opus" in info.model_id.lower()

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
    def mock_response_data(self):
        """Create mock API response data."""
        return {
            "id": "msg-test-123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "This is a test response."}],
            "model": "claude-haiku-4-20250514",
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

    def _mock_httpx_response(self, data: dict) -> MagicMock:
        """Create a mock httpx response."""
        mock = MagicMock()
        mock.json.return_value = data
        mock.raise_for_status = MagicMock()
        return mock

    @pytest.mark.asyncio
    async def test_complete_success(self, provider, mock_response_data):
        """Test successful completion."""
        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = self._mock_httpx_response(mock_response_data)
            response = await provider.complete("Hello, Claude!")
            assert response.content == "This is a test response."
            assert response.input_tokens == 100
            assert response.output_tokens == 50

    @pytest.mark.asyncio
    async def test_complete_with_system_prompt(self, provider, mock_response_data):
        """Test completion with system prompt."""
        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = self._mock_httpx_response(mock_response_data)
            response = await provider.complete(
                "Hello!", system_prompt="You are a helpful assistant."
            )
            assert response.content is not None

    @pytest.mark.asyncio
    async def test_complete_with_temperature(self, provider, mock_response_data):
        """Test completion with temperature setting."""
        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = self._mock_httpx_response(mock_response_data)
            response = await provider.complete("Hello!", temperature=0.5)
            assert response.content is not None

    @pytest.mark.asyncio
    async def test_complete_with_max_tokens(self, provider, mock_response_data):
        """Test completion with max tokens setting."""
        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = self._mock_httpx_response(mock_response_data)
            response = await provider.complete("Hello!", max_tokens=1000)
            assert response.content is not None

    @pytest.mark.asyncio
    async def test_handles_multiple_content_blocks(self, provider):
        """Test handling of multiple content blocks."""
        mock_data = {
            "id": "msg-test",
            "content": [
                {"type": "text", "text": "First part."},
                {"type": "text", "text": " Second part."},
            ],
            "usage": {"input_tokens": 10, "output_tokens": 10},
        }
        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = self._mock_httpx_response(mock_data)
            response = await provider.complete("Hello!")
            assert "First part" in response.content
            assert "Second part" in response.content


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
    async def test_handles_timeout_error(self, provider):
        """Test handling of timeout errors."""
        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
            mock.side_effect = httpx.TimeoutException("Timeout")
            with pytest.raises(Exception):
                await provider.complete("Hello!")

    @pytest.mark.asyncio
    async def test_handles_request_error(self, provider):
        """Test handling of request errors."""
        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
            mock.side_effect = httpx.RequestError("Connection failed")
            with pytest.raises(Exception):
                await provider.complete("Hello!")

    @pytest.mark.asyncio
    async def test_handles_empty_response(self, provider):
        """Test handling of empty response."""
        mock_data = {
            "id": "msg-test",
            "content": [],
            "usage": {"input_tokens": 10, "output_tokens": 0},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
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
        assert stats["total_requests"] == 0

    @pytest.mark.asyncio
    async def test_stats_increment_on_success(self, provider):
        """Test that stats increment on successful requests."""
        mock_data = {
            "id": "msg-test",
            "content": [{"type": "text", "text": "Response"}],
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            await provider.complete("Hello!")
            stats = provider.get_stats()
            assert stats["total_requests"] == 1
            # errors should be 0 on success
            assert stats["errors"] == 0


# ============================================================================
# Cost Calculation Tests
# ============================================================================


class TestAnthropicCostCalculation:
    """Tests for cost calculation."""

    @pytest.mark.parametrize(
        "model,expected_input_cost,expected_output_cost",
        [
            # Using the new model names from ANTHROPIC_MODELS
            ("claude-3-5-haiku-20241022", 0.25, 1.25),
            ("claude-haiku-4-20250514", 0.25, 1.25),
            ("claude-3-5-sonnet-20241022", 3.0, 15.0),
            ("claude-sonnet-4-20250514", 3.0, 15.0),
            ("claude-opus-4-20250514", 15.0, 75.0),
        ],
    )
    def test_model_pricing(self, model, expected_input_cost, expected_output_cost):
        """Test that model pricing is correct."""
        provider = AnthropicProvider(api_key="test-key", model=model)
        info = provider.get_model_info()
        assert info.input_cost_per_million == expected_input_cost
        assert info.output_cost_per_million == expected_output_cost


# ============================================================================
# Available Models Tests
# ============================================================================


class TestAnthropicAvailableModels:
    """Tests for available models."""

    def test_available_models_not_empty(self):
        """Test that available models dict is not empty."""
        assert len(ANTHROPIC_MODELS) > 0

    def test_available_models_have_required_fields(self):
        """Test that all models have required fields."""
        for model_id, info in ANTHROPIC_MODELS.items():
            assert info.model_id == model_id
            assert info.provider == "anthropic"
            assert info.context_length > 0
            assert info.input_cost_per_million >= 0
            assert info.output_cost_per_million >= 0

    def test_provider_exposes_available_models(self):
        """Test that provider exposes available models."""
        provider = AnthropicProvider(api_key="test-key")
        assert provider.available_models == ANTHROPIC_MODELS
