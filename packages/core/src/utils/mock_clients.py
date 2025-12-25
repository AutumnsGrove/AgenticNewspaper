"""Mock clients for testing without real API keys."""

from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class MockUsage:
    """Mock usage statistics."""
    input_tokens: int
    output_tokens: int


@dataclass
class MockContent:
    """Mock message content."""
    text: str
    type: str = "text"


@dataclass
class MockMessage:
    """Mock Anthropic message response."""
    id: str
    content: List[MockContent]
    model: str
    usage: MockUsage
    role: str = "assistant"
    type: str = "message"


class MockAnthropicClient:
    """Mock Anthropic client for testing."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.messages = MockMessages()


class MockMessages:
    """Mock messages interface."""

    def create(
        self,
        model: str,
        max_tokens: int,
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> MockMessage:
        """
        Create a mock message response.

        Args:
            model: Model name
            max_tokens: Maximum tokens to generate
            messages: List of message dicts
            **kwargs: Additional arguments

        Returns:
            MockMessage with simulated response
        """
        # Extract the user's message
        user_message = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        # Generate a mock response based on the input
        if "hello" in user_message.lower():
            response_text = "Hello from the Intelligent News Aggregator test!"
        elif "search" in user_message.lower():
            response_text = "Mock search results: Found 10 articles about AI and machine learning."
        elif "parse" in user_message.lower():
            response_text = "Mock parse result: Successfully extracted article content."
        elif "analyze" in user_message.lower():
            response_text = "Mock analysis: Relevance: 0.85, Quality: 0.78"
        elif "synthesize" in user_message.lower():
            response_text = "Mock synthesis: Generated HN-style digest with 12 articles."
        else:
            response_text = f"Mock response to: {user_message[:50]}..."

        # Simulate token usage (roughly estimate based on text length)
        input_tokens = sum(len(str(m.get("content", "")).split()) for m in messages) * 2
        output_tokens = len(response_text.split()) * 2

        return MockMessage(
            id="msg-mock-12345",
            content=[MockContent(text=response_text)],
            model=model,
            usage=MockUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
        )


def is_mock_key(api_key: str) -> bool:
    """
    Check if an API key is a mock key.

    Args:
        api_key: API key to check

    Returns:
        True if key is a mock, False otherwise
    """
    if not api_key:
        return True

    mock_indicators = [
        "mock",
        "test",
        "development",
        "fake",
        "not-real",
        "YOUR_KEY_HERE"
    ]

    return any(indicator in api_key.lower() for indicator in mock_indicators)


def get_anthropic_client(api_key: str):
    """
    Get Anthropic client (real or mock based on key).

    Args:
        api_key: Anthropic API key

    Returns:
        Anthropic client (real or mock)
    """
    if is_mock_key(api_key):
        print("⚠️  Using MOCK Anthropic client (no real API calls)")
        return MockAnthropicClient(api_key)
    else:
        from anthropic import Anthropic
        return Anthropic(api_key=api_key)
