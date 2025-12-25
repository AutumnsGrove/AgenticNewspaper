# LLM Provider Documentation

This document describes the LLM provider implementations.

## Overview

The system supports multiple LLM providers:
- **OpenRouter** (primary): Access to multiple models via single API
- **Anthropic** (fallback): Direct Claude API access

## Provider Interface

All providers implement a common interface:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class Message:
    role: str  # "user", "assistant", or "system"
    content: str

@dataclass
class GenerationConfig:
    model: str
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    stop_sequences: list[str] | None = None

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        messages: list[Message],
        config: GenerationConfig
    ) -> str:
        """Generate a response from the model."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        messages: list[Message],
        config: GenerationConfig,
        schema: dict
    ) -> dict:
        """Generate a structured response matching the schema."""
        pass
```

## OpenRouter Provider

Located at: `packages/core/src/providers/openrouter.py`

```python
class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str,
        default_model: str = "deepseek/deepseek-v3.2"
    ):
        self.api_key = api_key
        self.default_model = default_model
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://clearing.autumnsgrove.com",
                "X-Title": "The Daily Clearing",
            }
        )

    async def generate(
        self,
        messages: list[Message],
        config: GenerationConfig
    ) -> str:
        """Generate response using OpenRouter API."""
        response = await self._client.post(
            "/chat/completions",
            json={
                "model": config.model or self.default_model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "top_p": config.top_p,
                "stop": config.stop_sequences,
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
```

### Supported Models

| Model ID | Use Case | Cost |
|----------|----------|------|
| `deepseek/deepseek-v3.2` | Tier 1 agents | Low |
| `anthropic/claude-sonnet-4` | Tier 2 agents | Medium |
| `anthropic/claude-3.5-sonnet` | Alternative Tier 2 | Medium |
| `openai/gpt-4-turbo` | Alternative Tier 2 | High |

### Configuration

```python
from core.providers import OpenRouterProvider

provider = OpenRouterProvider(
    api_key="sk-or-...",
    default_model="deepseek/deepseek-v3.2"
)

# Use specific model
response = await provider.generate(
    messages=[Message(role="user", content="Hello")],
    config=GenerationConfig(model="anthropic/claude-sonnet-4")
)
```

## Anthropic Provider

Located at: `packages/core/src/providers/anthropic.py`

```python
class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

    BASE_URL = "https://api.anthropic.com/v1"

    def __init__(
        self,
        api_key: str,
        default_model: str = "claude-sonnet-4-20250514"
    ):
        self.api_key = api_key
        self.default_model = default_model
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
        )

    async def generate(
        self,
        messages: list[Message],
        config: GenerationConfig
    ) -> str:
        """Generate response using Anthropic API."""
        # Convert to Anthropic format
        anthropic_messages = []
        system_prompt = None

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                anthropic_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        payload = {
            "model": config.model or self.default_model,
            "messages": anthropic_messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
        }

        if system_prompt:
            payload["system"] = system_prompt

        response = await self._client.post("/messages", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]
```

### Supported Models

| Model ID | Use Case |
|----------|----------|
| `claude-sonnet-4-20250514` | Tier 2 reasoning |
| `claude-3-5-sonnet-20241022` | Previous Tier 2 |
| `claude-3-haiku-20240307` | Tier 1 fast tasks |

## Provider Factory

Located at: `packages/core/src/providers/factory.py`

```python
def create_provider(
    provider_type: str,
    api_key: str,
    **kwargs
) -> LLMProvider:
    """Create an LLM provider instance."""
    providers = {
        "openrouter": OpenRouterProvider,
        "anthropic": AnthropicProvider,
    }

    if provider_type not in providers:
        raise ValueError(f"Unknown provider: {provider_type}")

    return providers[provider_type](api_key=api_key, **kwargs)
```

### Usage

```python
from core.providers import create_provider

# OpenRouter (recommended)
provider = create_provider(
    "openrouter",
    api_key=os.environ["OPENROUTER_API_KEY"]
)

# Anthropic (fallback)
provider = create_provider(
    "anthropic",
    api_key=os.environ["ANTHROPIC_API_KEY"]
)
```

## Structured Output

For agents requiring structured data, use `generate_structured`:

```python
schema = {
    "type": "object",
    "properties": {
        "quality_score": {"type": "number", "minimum": 0, "maximum": 1},
        "reasoning": {"type": "string"},
        "dimensions": {
            "type": "object",
            "properties": {
                "credibility": {"type": "number"},
                "depth": {"type": "number"},
            }
        }
    },
    "required": ["quality_score", "reasoning"]
}

result = await provider.generate_structured(
    messages=[
        Message(role="system", content="Analyze article quality..."),
        Message(role="user", content=article.content)
    ],
    config=GenerationConfig(model="anthropic/claude-sonnet-4"),
    schema=schema
)

print(result["quality_score"])  # 0.85
```

## Error Handling

```python
from core.providers import ProviderError, RateLimitError

try:
    response = await provider.generate(messages, config)
except RateLimitError as e:
    # Wait and retry
    await asyncio.sleep(e.retry_after)
    response = await provider.generate(messages, config)
except ProviderError as e:
    # Log and handle
    logger.error(f"Provider error: {e}")
    raise
```

## Rate Limiting

Both providers implement automatic rate limiting:

```python
class OpenRouterProvider(LLMProvider):
    def __init__(self, ...):
        ...
        self._rate_limiter = RateLimiter(
            requests_per_minute=60,
            tokens_per_minute=100000
        )

    async def generate(self, ...):
        async with self._rate_limiter:
            return await self._make_request(...)
```

## Retry Logic

Automatic retries with exponential backoff:

```python
@retry(
    max_attempts=3,
    backoff_factor=2,
    exceptions=(httpx.HTTPStatusError,),
    exclude_status=(400, 401, 403)
)
async def _make_request(self, ...):
    ...
```

## Caching

Response caching for identical requests:

```python
class CachedProvider(LLMProvider):
    def __init__(self, provider: LLMProvider, cache_ttl: int = 3600):
        self.provider = provider
        self.cache = TTLCache(maxsize=1000, ttl=cache_ttl)

    async def generate(self, messages, config):
        cache_key = self._make_key(messages, config)

        if cache_key in self.cache:
            return self.cache[cache_key]

        response = await self.provider.generate(messages, config)
        self.cache[cache_key] = response
        return response
```

## Testing

Mock providers for testing:

```python
@pytest.fixture
def mock_provider():
    provider = MagicMock(spec=LLMProvider)
    provider.generate = AsyncMock(return_value="Mock response")
    provider.generate_structured = AsyncMock(return_value={"score": 0.8})
    return provider
```

Run provider tests:

```bash
cd packages/core
uv run pytest tests/providers/ -v
```
