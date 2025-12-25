"""Anthropic LLM provider implementation.

Direct integration with Anthropic's API for Claude models.
Used as a fallback when OpenRouter is unavailable.
"""

import time
from typing import Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .base import (
    BaseLLMProvider,
    LLMResponse,
    ModelInfo,
    ModelTier,
    ProviderError,
    RateLimitError,
    AuthenticationError,
    ModelNotFoundError,
    ContentFilterError,
)


# Model definitions for Anthropic direct API
ANTHROPIC_MODELS: dict[str, ModelInfo] = {
    "claude-3-5-haiku-20241022": ModelInfo(
        model_id="claude-3-5-haiku-20241022",
        name="Claude 3.5 Haiku",
        provider="anthropic",
        tier=ModelTier.TIER1,
        context_length=200000,
        input_cost_per_million=0.25,
        output_cost_per_million=1.25,
        supports_vision=True,
        description="Claude 3.5 Haiku - Fast and capable",
    ),
    "claude-haiku-4-20250514": ModelInfo(
        model_id="claude-haiku-4-20250514",
        name="Claude Haiku 4",
        provider="anthropic",
        tier=ModelTier.TIER1,
        context_length=200000,
        input_cost_per_million=0.25,
        output_cost_per_million=1.25,
        supports_vision=True,
        description="Claude Haiku 4 - Latest fast model",
    ),
    "claude-3-5-sonnet-20241022": ModelInfo(
        model_id="claude-3-5-sonnet-20241022",
        name="Claude 3.5 Sonnet",
        provider="anthropic",
        tier=ModelTier.TIER2,
        context_length=200000,
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        supports_vision=True,
        description="Claude 3.5 Sonnet - Balanced performance",
    ),
    "claude-sonnet-4-20250514": ModelInfo(
        model_id="claude-sonnet-4-20250514",
        name="Claude Sonnet 4",
        provider="anthropic",
        tier=ModelTier.TIER2,
        context_length=200000,
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        supports_vision=True,
        description="Claude Sonnet 4 - Latest balanced model",
    ),
    "claude-opus-4-20250514": ModelInfo(
        model_id="claude-opus-4-20250514",
        name="Claude Opus 4",
        provider="anthropic",
        tier=ModelTier.TIER3,
        context_length=200000,
        input_cost_per_million=15.00,
        output_cost_per_million=75.00,
        supports_vision=True,
        description="Claude Opus 4 - Most capable model",
    ),
}

# Default models by tier
DEFAULT_TIER1_MODEL = "claude-haiku-4-20250514"
DEFAULT_TIER2_MODEL = "claude-sonnet-4-20250514"


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic LLM provider.

    Provides direct access to Claude models via Anthropic's API.
    Used as a fallback when OpenRouter is unavailable.
    """

    BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_TIER1_MODEL,
        data_policy: str = "deny",
        timeout: float = 120.0,
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model identifier (e.g., "claude-sonnet-4-20250514")
            data_policy: Data retention policy (not directly supported, for interface consistency)
            timeout: Request timeout in seconds
        """
        super().__init__(api_key, model, data_policy)
        self.timeout = timeout

        # Validate model
        if model not in ANTHROPIC_MODELS:
            raise ModelNotFoundError(
                f"Unknown model: {model}. Available: {list(ANTHROPIC_MODELS.keys())}",
                provider="anthropic",
            )

        # Create HTTP client
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=timeout,
            headers=self._build_headers(),
        )

    def _build_headers(self) -> dict[str, str]:
        """Build request headers."""
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "Content-Type": "application/json",
        }

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "anthropic"

    @property
    def available_models(self) -> dict[str, ModelInfo]:
        """Return available models with their info."""
        return ANTHROPIC_MODELS

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(RateLimitError),
        reraise=True,
    )
    async def complete(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: str | None = None,
        stop_sequences: list[str] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Complete a prompt using Anthropic's API.

        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            system_prompt: Optional system prompt
            stop_sequences: Optional stop sequences
            **kwargs: Additional arguments (top_p, top_k, etc.)

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            ProviderError: If the request fails
            RateLimitError: If rate limit is exceeded
            AuthenticationError: If authentication fails
        """
        start_time = time.time()

        # Build messages
        messages = [{"role": "user", "content": prompt}]

        # Build request payload
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Add optional parameters
        if system_prompt:
            payload["system"] = system_prompt
        if stop_sequences:
            payload["stop_sequences"] = stop_sequences
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            payload["top_k"] = kwargs["top_k"]

        try:
            response = await self._client.post("/messages", json=payload)
            response.raise_for_status()
            data = response.json()

        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)

        except httpx.TimeoutException:
            self.record_error()
            raise ProviderError(
                f"Request timed out after {self.timeout}s",
                provider="anthropic",
            )

        except httpx.RequestError as e:
            self.record_error()
            raise ProviderError(
                f"Request failed: {str(e)}",
                provider="anthropic",
            )

        # Parse response
        try:
            content_blocks = data.get("content", [])
            content = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    content += block.get("text", "")

            finish_reason = data.get("stop_reason", "end_turn")

            usage = data.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

        except (KeyError, IndexError) as e:
            self.record_error()
            raise ProviderError(
                f"Invalid response format: {str(e)}",
                provider="anthropic",
                details={"response": data},
            )

        # Calculate cost
        cost = self.calculate_cost(input_tokens, output_tokens)
        response_time = time.time() - start_time

        # Build response
        llm_response = LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            response_time_seconds=response_time,
            finish_reason=finish_reason,
            metadata={
                "message_id": data.get("id"),
                "model_version": data.get("model"),
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )

        # Update stats
        self.update_stats(llm_response)

        return llm_response

    def _handle_http_error(self, error: httpx.HTTPStatusError) -> None:
        """Handle HTTP errors from Anthropic."""
        status_code = error.response.status_code

        try:
            error_data = error.response.json()
            error_type = error_data.get("error", {}).get("type", "")
            error_message = error_data.get("error", {}).get("message", str(error))
        except Exception:
            error_type = ""
            error_message = str(error)

        if status_code == 401:
            self.record_error()
            raise AuthenticationError(
                f"Invalid API key: {error_message}",
                provider="anthropic",
            )

        elif status_code == 429:
            self.record_error(is_rate_limit=True)
            retry_after = error.response.headers.get("Retry-After")
            raise RateLimitError(
                f"Rate limit exceeded: {error_message}",
                provider="anthropic",
                retry_after=float(retry_after) if retry_after else None,
            )

        elif status_code == 404 or error_type == "invalid_request_error":
            if "model" in error_message.lower():
                self.record_error()
                raise ModelNotFoundError(
                    f"Model not found: {error_message}",
                    provider="anthropic",
                )
            else:
                self.record_error()
                raise ProviderError(
                    f"Invalid request: {error_message}",
                    provider="anthropic",
                )

        elif error_type == "invalid_api_key":
            self.record_error()
            raise AuthenticationError(
                f"Invalid API key: {error_message}",
                provider="anthropic",
            )

        else:
            self.record_error()
            raise ProviderError(
                f"Request failed ({status_code}): {error_message}",
                provider="anthropic",
                details={"status_code": status_code, "error_type": error_type},
            )

    async def health_check(self) -> bool:
        """
        Check if Anthropic is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Use a minimal request to check health
            response = await self.complete(
                prompt="Hi",
                max_tokens=5,
                temperature=0.0,
            )
            return len(response.content) > 0
        except Exception:
            return False

    async def count_tokens(self, text: str) -> int:
        """
        Count tokens for text using Anthropic's tokenizer endpoint.

        Args:
            text: Text to count tokens for

        Returns:
            Token count
        """
        try:
            response = await self._client.post(
                "/messages/count_tokens",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": text}],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("input_tokens", self.estimate_tokens(text))
        except Exception:
            return self.estimate_tokens(text)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
