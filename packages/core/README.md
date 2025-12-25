# The Daily Clearing - Core Package

Python package containing AI agents, LLM providers, and database layers for The Daily Clearing news aggregator.

## Installation

```bash
uv sync
```

## Components

- **Providers**: OpenRouter and Anthropic LLM integrations
- **Agents**: Quality, Bias, and Connection analysis agents
- **Services**: Tavily search and newspaper3k parsing
- **Database**: SQLite persistence layer

## Testing

```bash
uv run pytest tests/ -v
```

## Usage

```python
from core.providers import create_provider
from core.services import SearchService, ParserService

# Create provider
provider = create_provider("openrouter", api_key="...")

# Search for articles
search = SearchService(tavily_api_key="...")
results = await search.search("AI news", max_results=10)

# Parse article content
parser = ParserService()
article = await parser.parse(url)
```
