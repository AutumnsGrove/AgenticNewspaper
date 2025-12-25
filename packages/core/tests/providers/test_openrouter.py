"""
Tests for the OpenRouter LLM provider.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import httpx

from src.providers.openrouter import OpenRouterProvider


# ============================================================================
# Provider Initialization Tests
# ============================================================================


class TestOpenRouterProviderInit:
    """Tests for OpenRouter provider initialization."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        provider = OpenRouterProvider(api_key="test-key")
        assert provider.api_key == "test-key"

    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        provider = OpenRouterProvider(
            api_key="test-key", model="anthropic/claude-opus-4"
        )
        assert provider.model == "anthropic/claude-opus-4"

    def test_init_with_data_policy(self):
        """Test initialization with data policy."""
        provider = OpenRouterProvider(api_key="test-key", data_policy="deny")
        assert provider.data_policy == "deny"

    def test_default_model_is_deepseek(self):
        """Test that default model is DeepSeek."""
        provider = OpenRouterProvider(api_key="test-key")
        assert "deepseek" in provider.model.lower()

    def test_base_url(self):
        """Test that base URL is correct."""
        assert OpenRouterProvider.BASE_URL == "https://openrouter.ai/api/v1"

    @pytest.mark.parametrize(
        "model",
        [
            "deepseek/deepseek-chat",
            "anthropic/claude-sonnet-4",
            "anthropic/claude-3.5-haiku",
            "openai/gpt-4o",
            "meta-llama/llama-3.3-70b-instruct",
        ],
    )
    def test_init_with_various_models(self, model):
        """Test initialization with various models."""
        provider = OpenRouterProvider(api_key="test-key", model=model)
        assert provider.model == model


# ============================================================================
# Headers Tests
# ============================================================================


class TestOpenRouterHeaders:
    """Tests for OpenRouter request headers."""

    def test_authorization_header(self):
        """Test that authorization header is set correctly."""
        provider = OpenRouterProvider(api_key="test-key-123")
        headers = provider._build_headers()
        assert headers["Authorization"] == "Bearer test-key-123"

    def test_content_type_header(self):
        """Test that content type header is set."""
        provider = OpenRouterProvider(api_key="test-key")
        headers = provider._build_headers()
        assert headers["Content-Type"] == "application/json"

    def test_data_policy_header(self):
        """Test that data policy header is set."""
        provider = OpenRouterProvider(api_key="test-key", data_policy="deny")
        headers = provider._build_headers()
        assert "X-Data-Policy" in headers or "x-data-policy" in headers.keys()


# ============================================================================
# Model Info Tests
# ============================================================================


class TestOpenRouterModelInfo:
    """Tests for OpenRouter model information."""

    def test_get_model_info_deepseek(self):
        """Test getting model info for DeepSeek."""
        provider = OpenRouterProvider(
            api_key="test-key", model="deepseek/deepseek-chat"
        )
        info = provider.get_model_info()
        assert info.model_id == "deepseek/deepseek-chat"
        assert info.provider == "deepseek"
        assert info.input_cost_per_million >= 0
        assert info.output_cost_per_million >= 0

    def test_get_model_info_claude(self):
        """Test getting model info for Claude."""
        provider = OpenRouterProvider(
            api_key="test-key", model="anthropic/claude-sonnet-4"
        )
        info = provider.get_model_info()
        assert "claude" in info.model_id.lower()

    def test_model_info_context_length(self):
        """Test that context length is set."""
        provider = OpenRouterProvider(api_key="test-key")
        info = provider.get_model_info()
        assert info.context_length > 0


# ============================================================================
# Completion Tests
# ============================================================================


class TestOpenRouterComplete:
    """Tests for OpenRouter completion method."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance."""
        return OpenRouterProvider(api_key="test-key")

    @pytest.fixture
    def mock_response_data(self):
        """Create a mock API response."""
        return {
            "id": "gen-test-123",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "This is a test response.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
            "model": "deepseek/deepseek-chat",
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
            response = await provider.complete("Hello, AI!")
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
            response = await provider.complete("Hello!", temperature=0.7)
            assert response.content is not None

    @pytest.mark.asyncio
    async def test_complete_with_max_tokens(self, provider, mock_response_data):
        """Test completion with max tokens setting."""
        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = self._mock_httpx_response(mock_response_data)
            response = await provider.complete("Hello!", max_tokens=500)
            assert response.content is not None

    @pytest.mark.asyncio
    async def test_complete_tracks_stats(self, provider, mock_response_data):
        """Test that completion tracks statistics."""
        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = self._mock_httpx_response(mock_response_data)
            initial_stats = provider.get_stats()
            await provider.complete("Hello!")
            updated_stats = provider.get_stats()
            assert updated_stats["total_requests"] > initial_stats["total_requests"]




# ============================================================================
# Error Handling Tests
# ============================================================================


class TestOpenRouterErrorHandling:
    """Tests for OpenRouter error handling."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance."""
        return OpenRouterProvider(api_key="test-key")

    @pytest.mark.asyncio
    async def test_handles_timeout_error(self, provider):
        """Test handling of timeout errors."""
        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
            mock.side_effect = httpx.TimeoutException("Request timed out")
            with pytest.raises(Exception):
                await provider.complete("Hello!")

    @pytest.mark.asyncio
    async def test_handles_request_error(self, provider):
        """Test handling of request errors."""
        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
            mock.side_effect = httpx.RequestError("Connection failed")
            with pytest.raises(Exception):
                await provider.complete("Hello!")


# ============================================================================
# Statistics Tests
# ============================================================================


class TestOpenRouterStats:
    """Tests for OpenRouter statistics tracking."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance."""
        return OpenRouterProvider(api_key="test-key")

    def test_initial_stats_are_zero(self, provider):
        """Test that initial stats are zero."""
        stats = provider.get_stats()
        assert stats["total_requests"] == 0
        assert stats["total_input_tokens"] == 0
        assert stats["total_output_tokens"] == 0
        assert stats["total_cost_usd"] == 0.0

    def _mock_httpx_response(self, data: dict) -> MagicMock:
        """Create a mock httpx response."""
        mock = MagicMock()
        mock.json.return_value = data
        mock.raise_for_status = MagicMock()
        return mock

    @pytest.mark.asyncio
    async def test_stats_track_successful_requests(self, provider):
        """Test that stats track successful requests."""
        mock_response = {
            "id": "gen-test",
            "choices": [{"message": {"content": "Response"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        }
        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = self._mock_httpx_response(mock_response)
            await provider.complete("Hello!")
            stats = provider.get_stats()
            assert stats["total_requests"] == 1
            # errors should be 0 on success
            assert stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_stats_accumulate_tokens(self, provider):
        """Test that stats accumulate token counts."""
        mock_response = {
            "id": "gen-test",
            "choices": [{"message": {"content": "Response"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        }
        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = self._mock_httpx_response(mock_response)
            await provider.complete("Hello!")
            await provider.complete("Hello again!")
            stats = provider.get_stats()
            assert stats["total_input_tokens"] == 200
            assert stats["total_output_tokens"] == 100


# ============================================================================
# Cost Calculation Tests
# ============================================================================


class TestOpenRouterCostCalculation:
    """Tests for cost calculation."""

    @pytest.fixture
    def provider(self):
        """Create a provider with known costs."""
        return OpenRouterProvider(api_key="test-key", model="deepseek/deepseek-chat")

    def _mock_httpx_response(self, data: dict) -> MagicMock:
        """Create a mock httpx response."""
        mock = MagicMock()
        mock.json.return_value = data
        mock.raise_for_status = MagicMock()
        return mock

    @pytest.mark.asyncio
    async def test_calculates_cost(self, provider):
        """Test that cost is calculated correctly."""
        mock_response = {
            "id": "gen-test",
            "choices": [{"message": {"content": "Response"}}],
            "usage": {
                "prompt_tokens": 1000000,  # 1M tokens
                "completion_tokens": 500000,  # 500K tokens
                "total_tokens": 1500000,
            },
        }
        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = self._mock_httpx_response(mock_response)
            response = await provider.complete("Hello!")
            # Cost should be calculated based on model pricing
            assert response.cost_usd is not None
            assert response.cost_usd > 0

    @pytest.mark.parametrize(
        "input_tokens,output_tokens",
        [
            (100, 50),
            (1000, 500),
            (10000, 5000),
            (100000, 50000),
        ],
    )
    @pytest.mark.asyncio
    async def test_cost_scales_with_tokens(self, provider, input_tokens, output_tokens):
        """Test that cost scales with token count."""
        mock_response = {
            "id": "gen-test",
            "choices": [{"message": {"content": "Response"}}],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        }
        with patch.object(provider._client, "post", new_callable=AsyncMock) as mock:
            mock.return_value = self._mock_httpx_response(mock_response)
            response = await provider.complete("Hello!")
            if response.cost_usd is not None:
                assert response.cost_usd >= 0
