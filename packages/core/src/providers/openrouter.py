"""OpenRouter LLM provider implementation.

OpenRouter provides unified access to many LLM models including:
- DeepSeek V3/V3.2 (extremely cost-effective)
- Claude models (Haiku, Sonnet, Opus)
- GPT-4, Gemini, Llama, and more

This is the default provider for The Daily Clearing due to:
1. Cost efficiency (DeepSeek is ~10x cheaper than Claude)
2. Model flexibility (easy switching between providers)
3. Zero data retention with X-Data-Policy header
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


# Model definitions for OpenRouter
OPENROUTER_MODELS: dict[str, ModelInfo] = {
    # DeepSeek models (Tier 1 & 2 - extremely cost-effective)
    "deepseek/deepseek-chat": ModelInfo(
        model_id="deepseek/deepseek-chat",
        name="DeepSeek V3",
        provider="deepseek",
        tier=ModelTier.TIER1,
        context_length=64000,
        input_cost_per_million=0.27,
        output_cost_per_million=1.10,
        supports_vision=False,
        description="DeepSeek V3 - Cost-effective model with strong reasoning",
    ),
    "deepseek/deepseek-r1": ModelInfo(
        model_id="deepseek/deepseek-r1",
        name="DeepSeek R1",
        provider="deepseek",
        tier=ModelTier.TIER2,
        context_length=64000,
        input_cost_per_million=0.55,
        output_cost_per_million=2.19,
        supports_vision=False,
        description="DeepSeek R1 - Enhanced reasoning with chain-of-thought",
    ),
    # Claude models (Tier 2 & 3 - premium quality)
    "anthropic/claude-3.5-haiku": ModelInfo(
        model_id="anthropic/claude-3.5-haiku",
        name="Claude 3.5 Haiku",
        provider="anthropic",
        tier=ModelTier.TIER1,
        context_length=200000,
        input_cost_per_million=0.80,
        output_cost_per_million=4.00,
        supports_vision=True,
        description="Claude 3.5 Haiku - Fast and capable",
    ),
    "anthropic/claude-sonnet-4": ModelInfo(
        model_id="anthropic/claude-sonnet-4",
        name="Claude Sonnet 4",
        provider="anthropic",
        tier=ModelTier.TIER2,
        context_length=200000,
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        supports_vision=True,
        description="Claude Sonnet 4 - Balanced performance and cost",
    ),
    "anthropic/claude-opus-4": ModelInfo(
        model_id="anthropic/claude-opus-4",
        name="Claude Opus 4",
        provider="anthropic",
        tier=ModelTier.TIER3,
        context_length=200000,
        input_cost_per_million=15.00,
        output_cost_per_million=75.00,
        supports_vision=True,
        description="Claude Opus 4 - Most capable Claude model",
    ),
    # GPT models
    "openai/gpt-4o": ModelInfo(
        model_id="openai/gpt-4o",
        name="GPT-4o",
        provider="openai",
        tier=ModelTier.TIER2,
        context_length=128000,
        input_cost_per_million=2.50,
        output_cost_per_million=10.00,
        supports_vision=True,
        description="OpenAI GPT-4o - Multimodal flagship",
    ),
    "openai/gpt-4o-mini": ModelInfo(
        model_id="openai/gpt-4o-mini",
        name="GPT-4o Mini",
        provider="openai",
        tier=ModelTier.TIER1,
        context_length=128000,
        input_cost_per_million=0.15,
        output_cost_per_million=0.60,
        supports_vision=True,
        description="OpenAI GPT-4o Mini - Fast and affordable",
    ),
    # Google Gemini
    "google/gemini-2.0-flash-exp": ModelInfo(
        model_id="google/gemini-2.0-flash-exp",
        name="Gemini 2.0 Flash",
        provider="google",
        tier=ModelTier.TIER1,
        context_length=1000000,
        input_cost_per_million=0.10,
        output_cost_per_million=0.40,
        supports_vision=True,
        description="Google Gemini 2.0 Flash - Fast with massive context",
    ),
    # Llama models
    "meta-llama/llama-3.3-70b-instruct": ModelInfo(
        model_id="meta-llama/llama-3.3-70b-instruct",
        name="Llama 3.3 70B",
        provider="meta",
        tier=ModelTier.TIER1,
        context_length=128000,
        input_cost_per_million=0.40,
        output_cost_per_million=0.40,
        supports_vision=False,
        description="Meta Llama 3.3 70B - Open source powerhouse",
    ),
}

# Default models by tier
DEFAULT_TIER1_MODEL = "deepseek/deepseek-chat"
DEFAULT_TIER2_MODEL = "deepseek/deepseek-chat"  # Can use same model, prompts differ


class OpenRouterProvider(BaseLLMProvider):
    """
    OpenRouter LLM provider.

    Provides access to multiple LLM providers through a unified API.
    Uses zero data retention by default via X-Data-Policy header.
    """

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_TIER1_MODEL,
        data_policy: str = "deny",
        site_url: str = "https://clearing.autumnsgrove.com",
        site_name: str = "The Daily Clearing",
        timeout: float = 120.0,
    ):
        """
        Initialize OpenRouter provider.

        Args:
            api_key: OpenRouter API key
            model: Model identifier (e.g., "deepseek/deepseek-chat")
            data_policy: Data retention policy ("deny" for zero retention)
            site_url: Your site URL (for OpenRouter rankings)
            site_name: Your site name (for OpenRouter rankings)
            timeout: Request timeout in seconds
        """
        super().__init__(api_key, model, data_policy)
        self.site_url = site_url
        self.site_name = site_name
        self.timeout = timeout

        # Validate model
        if model not in OPENROUTER_MODELS:
            raise ModelNotFoundError(
                f"Unknown model: {model}. Available: {list(OPENROUTER_MODELS.keys())}",
                provider="openrouter",
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
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name,
            "X-Data-Policy": self.data_policy,
            "Content-Type": "application/json",
        }

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "openrouter"

    @property
    def available_models(self) -> dict[str, ModelInfo]:
        """Return available models with their info."""
        return OPENROUTER_MODELS

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
        Complete a prompt using OpenRouter.

        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-2)
            system_prompt: Optional system prompt
            stop_sequences: Optional stop sequences
            **kwargs: Additional arguments (top_p, frequency_penalty, etc.)

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            ProviderError: If the request fails
            RateLimitError: If rate limit is exceeded
            AuthenticationError: If authentication fails
        """
        start_time = time.time()

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Build request payload
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Add optional parameters
        if stop_sequences:
            payload["stop"] = stop_sequences
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "frequency_penalty" in kwargs:
            payload["frequency_penalty"] = kwargs["frequency_penalty"]
        if "presence_penalty" in kwargs:
            payload["presence_penalty"] = kwargs["presence_penalty"]

        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)

        except httpx.TimeoutException:
            self.record_error()
            raise ProviderError(
                f"Request timed out after {self.timeout}s",
                provider="openrouter",
            )

        except httpx.RequestError as e:
            self.record_error()
            raise ProviderError(
                f"Request failed: {str(e)}",
                provider="openrouter",
            )

        # Parse response
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason", "stop")

            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

        except (KeyError, IndexError) as e:
            self.record_error()
            raise ProviderError(
                f"Invalid response format: {str(e)}",
                provider="openrouter",
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
                "openrouter_id": data.get("id"),
                "system_fingerprint": data.get("system_fingerprint"),
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )

        # Update stats
        self.update_stats(llm_response)

        return llm_response

    def _handle_http_error(self, error: httpx.HTTPStatusError) -> None:
        """Handle HTTP errors from OpenRouter."""
        status_code = error.response.status_code

        try:
            error_data = error.response.json()
            error_message = error_data.get("error", {}).get("message", str(error))
        except Exception:
            error_message = str(error)

        if status_code == 401:
            self.record_error()
            raise AuthenticationError(
                f"Invalid API key: {error_message}",
                provider="openrouter",
            )

        elif status_code == 429:
            self.record_error(is_rate_limit=True)
            retry_after = error.response.headers.get("Retry-After")
            raise RateLimitError(
                f"Rate limit exceeded: {error_message}",
                provider="openrouter",
                retry_after=float(retry_after) if retry_after else None,
            )

        elif status_code == 404:
            self.record_error()
            raise ModelNotFoundError(
                f"Model not found: {error_message}",
                provider="openrouter",
            )

        elif status_code == 400 and "content" in error_message.lower():
            self.record_error()
            raise ContentFilterError(
                f"Content filtered: {error_message}",
                provider="openrouter",
            )

        else:
            self.record_error()
            raise ProviderError(
                f"Request failed ({status_code}): {error_message}",
                provider="openrouter",
                details={"status_code": status_code},
            )

    async def health_check(self) -> bool:
        """
        Check if OpenRouter is healthy and accessible.

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

    async def get_credits(self) -> dict[str, Any]:
        """
        Get current credit balance from OpenRouter.

        Returns:
            Dictionary with credit information
        """
        try:
            response = await self._client.get("/auth/key")
            response.raise_for_status()
            data = response.json()
            return {
                "limit": data.get("limit"),
                "usage": data.get("usage"),
                "remaining": data.get("limit", 0) - data.get("usage", 0),
            }
        except Exception as e:
            return {"error": str(e)}

    async def list_available_models(self) -> list[dict[str, Any]]:
        """
        List all models available on OpenRouter.

        Returns:
            List of model information dictionaries
        """
        try:
            response = await self._client.get("/models")
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception:
            return []

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
