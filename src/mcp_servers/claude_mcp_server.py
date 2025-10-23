"""Claude MCP server implementation."""

import time
from typing import Optional
from .base_provider import BaseLLMProvider, LLMResponse
from ..utils.mock_clients import get_anthropic_client, is_mock_key


class ClaudeMCPServer(BaseLLMProvider):
    """MCP server for Claude models (Haiku and Sonnet)."""

    # Pricing per million tokens (input, output)
    PRICING = {
        "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25},
        "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        "claude-haiku-4-20250514": {"input": 0.25, "output": 1.25},
    }

    def __init__(self, api_key: str, model: str):
        """
        Initialize Claude MCP server.

        Args:
            api_key: Anthropic API key
            model: Claude model identifier
        """
        super().__init__(api_key, model)
        self.client = get_anthropic_client(api_key)
        self.is_mock = is_mock_key(api_key)

        # Validate model
        if model not in self.PRICING:
            raise ValueError(
                f"Unknown Claude model: {model}. "
                f"Available: {list(self.PRICING.keys())}"
            )

    async def complete(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Complete a prompt using Claude.

        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            system_prompt: Optional system prompt
            **kwargs: Additional arguments (top_p, etc.)

        Returns:
            LLMResponse with content and metadata
        """
        start_time = time.time()

        # Build messages
        messages = [{"role": "user", "content": prompt}]

        # Build request parameters
        request_params = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }

        # Add system prompt if provided
        if system_prompt:
            request_params["system"] = system_prompt

        # Make API call
        response = self.client.messages.create(**request_params)

        # Extract response data
        content = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = self.get_cost(input_tokens, output_tokens)

        response_time = time.time() - start_time

        # Create LLM response
        llm_response = LLMResponse(
            content=content,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            response_time_seconds=response_time,
            metadata={
                "is_mock": self.is_mock,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )

        # Update stats
        self.update_stats(llm_response)

        return llm_response

    def get_token_count(self, text: str) -> int:
        """
        Estimate token count (rough approximation).

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        # Rough estimate: ~4 characters per token for English
        # This is not exact - for production, use tiktoken or similar
        return len(text) // 4

    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost in USD.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        if self.model not in self.PRICING:
            return 0.0

        pricing = self.PRICING[self.model]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    async def health_check(self) -> bool:
        """
        Check if Claude API is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Simple health check: send minimal request
            response = await self.complete(
                prompt="ping",
                max_tokens=10,
                temperature=0.0
            )
            return len(response.content) > 0
        except Exception:
            return False

    def get_tier_name(self) -> str:
        """
        Get tier name based on model.

        Returns:
            "tier1" for Haiku, "tier2" for Sonnet
        """
        if "haiku" in self.model.lower():
            return "tier1"
        elif "sonnet" in self.model.lower():
            return "tier2"
        else:
            return "unknown"
