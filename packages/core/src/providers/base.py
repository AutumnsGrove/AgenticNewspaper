"""Base LLM provider interface and common types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ProviderError(Exception):
    """Base exception for provider errors."""

    def __init__(self, message: str, provider: str = "unknown", details: dict | None = None):
        super().__init__(message)
        self.provider = provider
        self.details = details or {}


class RateLimitError(ProviderError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        provider: str = "unknown",
        retry_after: float | None = None,
        details: dict | None = None,
    ):
        super().__init__(message, provider, details)
        self.retry_after = retry_after


class AuthenticationError(ProviderError):
    """Raised when authentication fails."""

    pass


class ModelNotFoundError(ProviderError):
    """Raised when requested model is not available."""

    pass


class ContentFilterError(ProviderError):
    """Raised when content is blocked by provider's safety filters."""

    pass


class ModelTier(Enum):
    """Model tier for cost/capability tradeoffs."""

    TIER1 = "tier1"  # Fast, cheap (DeepSeek, Haiku)
    TIER2 = "tier2"  # Smart, capable (DeepSeek, Sonnet)
    TIER3 = "tier3"  # Premium (Opus, GPT-4)


@dataclass
class ModelInfo:
    """Information about an LLM model."""

    model_id: str
    name: str
    provider: str
    tier: ModelTier
    context_length: int
    input_cost_per_million: float
    output_cost_per_million: float
    supports_vision: bool = False
    supports_function_calling: bool = True
    supports_streaming: bool = True
    description: str = ""

    @property
    def input_cost_per_token(self) -> float:
        """Cost per input token in USD."""
        return self.input_cost_per_million / 1_000_000

    @property
    def output_cost_per_token(self) -> float:
        """Cost per output token in USD."""
        return self.output_cost_per_million / 1_000_000


@dataclass
class LLMResponse:
    """Response from an LLM completion request."""

    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    response_time_seconds: float
    finish_reason: str = "stop"
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens

    @property
    def tokens_per_second(self) -> float:
        """Output tokens per second."""
        if self.response_time_seconds <= 0:
            return 0.0
        return self.output_tokens / self.response_time_seconds

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "response_time_seconds": self.response_time_seconds,
            "tokens_per_second": self.tokens_per_second,
            "finish_reason": self.finish_reason,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ProviderStats:
    """Statistics for a provider instance."""

    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    total_response_time: float = 0.0
    errors: int = 0
    rate_limits_hit: int = 0

    @property
    def average_response_time(self) -> float:
        """Average response time in seconds."""
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time / self.total_requests

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage."""
        total = self.total_requests + self.errors
        if total == 0:
            return 100.0
        return (self.total_requests / total) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_requests": self.total_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost_usd": self.total_cost_usd,
            "total_response_time": self.total_response_time,
            "average_response_time": self.average_response_time,
            "errors": self.errors,
            "rate_limits_hit": self.rate_limits_hit,
            "success_rate": self.success_rate,
        }


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, api_key: str, model: str, data_policy: str = "deny"):
        """
        Initialize provider.

        Args:
            api_key: API key for authentication
            model: Model identifier to use
            data_policy: Data retention policy ("deny" for zero retention)
        """
        self.api_key = api_key
        self.model = model
        self.data_policy = data_policy
        self._stats = ProviderStats()

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass

    @property
    @abstractmethod
    def available_models(self) -> dict[str, ModelInfo]:
        """Return available models with their info."""
        pass

    @abstractmethod
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
        Complete a prompt.

        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-2)
            system_prompt: Optional system prompt
            stop_sequences: Optional stop sequences
            **kwargs: Additional provider-specific arguments

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            ProviderError: If the request fails
            RateLimitError: If rate limit is exceeded
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        pass

    def get_model_info(self, model_id: str | None = None) -> ModelInfo | None:
        """
        Get information about a model.

        Args:
            model_id: Model ID (uses current model if None)

        Returns:
            ModelInfo if found, None otherwise
        """
        model_id = model_id or self.model
        return self.available_models.get(model_id)

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for a request.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        model_info = self.get_model_info()
        if not model_info:
            return 0.0

        input_cost = input_tokens * model_info.input_cost_per_token
        output_cost = output_tokens * model_info.output_cost_per_token
        return input_cost + output_cost

    def update_stats(self, response: LLMResponse) -> None:
        """
        Update provider statistics.

        Args:
            response: LLM response to record
        """
        self._stats.total_requests += 1
        self._stats.total_input_tokens += response.input_tokens
        self._stats.total_output_tokens += response.output_tokens
        self._stats.total_cost_usd += response.cost_usd
        self._stats.total_response_time += response.response_time_seconds

    def record_error(self, is_rate_limit: bool = False) -> None:
        """
        Record an error.

        Args:
            is_rate_limit: Whether this was a rate limit error
        """
        self._stats.errors += 1
        if is_rate_limit:
            self._stats.rate_limits_hit += 1

    def get_stats(self) -> dict[str, Any]:
        """
        Get provider statistics.

        Returns:
            Dictionary with provider stats
        """
        return {
            "provider": self.provider_name,
            "model": self.model,
            **self._stats.to_dict(),
        }

    def reset_stats(self) -> None:
        """Reset provider statistics."""
        self._stats = ProviderStats()

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        This is a rough approximation. For exact counts,
        use the provider's tokenizer.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Rough estimate: ~4 characters per token for English
        return len(text) // 4
