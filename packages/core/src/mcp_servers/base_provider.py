"""Base class for LLM providers accessed via MCP."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LLMResponse:
    """Standard response from LLM provider."""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    response_time_seconds: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata if None."""
        if self.metadata is None:
            self.metadata = {}

    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "response_time_seconds": self.response_time_seconds,
            "metadata": self.metadata
        }


class BaseLLMProvider(ABC):
    """Base class for LLM providers accessed via MCP."""

    def __init__(self, api_key: str, model: str):
        """
        Initialize provider.

        Args:
            api_key: API key for the provider
            model: Model identifier
        """
        self.api_key = api_key
        self.model = model
        self._request_count = 0
        self._total_tokens = 0
        self._total_cost = 0.0

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Complete a prompt and return response + metadata.

        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            system_prompt: Optional system prompt
            **kwargs: Additional provider-specific arguments

        Returns:
            LLMResponse with content and metadata
        """
        pass

    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Token count
        """
        pass

    @abstractmethod
    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost in USD.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        pass

    def update_stats(self, response: LLMResponse):
        """
        Update provider statistics.

        Args:
            response: LLM response to track
        """
        self._request_count += 1
        self._total_tokens += response.total_tokens
        self._total_cost += response.cost_usd

    def get_stats(self) -> Dict[str, Any]:
        """
        Get provider usage statistics.

        Returns:
            Dictionary with usage stats
        """
        return {
            "provider": self.__class__.__name__,
            "model": self.model,
            "request_count": self._request_count,
            "total_tokens": self._total_tokens,
            "total_cost_usd": round(self._total_cost, 4),
            "avg_tokens_per_request": (
                self._total_tokens // self._request_count
                if self._request_count > 0 else 0
            ),
            "avg_cost_per_request": (
                self._total_cost / self._request_count
                if self._request_count > 0 else 0.0
            )
        }

    def reset_stats(self):
        """Reset usage statistics."""
        self._request_count = 0
        self._total_tokens = 0
        self._total_cost = 0.0

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if provider is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        pass

    def __str__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(model={self.model})"
