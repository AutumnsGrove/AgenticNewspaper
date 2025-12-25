# Agent Implementations

This document describes the AI agent implementations in the core package.

## Overview

The system uses a tiered agent architecture:
- **Tier 1**: Fast execution agents using Claude Haiku
- **Tier 2**: Deep reasoning agents using Claude Sonnet

## Tier 1 Agents

### Search Agent

Located at: `packages/core/src/agents/search_agent.py`

The Search Agent discovers news articles using the Tavily Search API.

```python
class SearchAgent:
    """Agent for discovering news articles via Tavily."""

    async def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "advanced"
    ) -> list[SearchResult]
```

**Features:**
- Advanced search depth for comprehensive results
- Domain filtering (include/exclude)
- Time-based filtering (past hour, day, week)
- Topic-based search queries

**Configuration:**
```python
{
    "api_key": "tavily-api-key",
    "search_depth": "advanced",
    "max_results": 10,
    "include_domains": [],
    "exclude_domains": []
}
```

### Fetch Agent

Located at: `packages/core/src/agents/fetch_agent.py`

The Fetch Agent retrieves full article content from URLs.

```python
class FetchAgent:
    """Agent for fetching article content."""

    async def fetch(self, url: str) -> FetchResult
```

**Features:**
- Async HTTP client with connection pooling
- Rate limiting and retry logic
- User-agent rotation
- Timeout handling

### Parser Agent

Located at: `packages/core/src/agents/parser_agent.py`

The Parser Agent extracts structured content from HTML using newspaper3k.

```python
class ParserAgent:
    """Agent for parsing article content."""

    async def parse(self, html: str, url: str) -> ParsedArticle
```

**Extracted Fields:**
- Title
- Authors
- Publish date
- Content text
- Top image
- Meta description
- Keywords

## Tier 2 Agents

### Quality Agent

Located at: `packages/core/src/agents/quality_agent.py`

The Quality Agent assesses article quality using Claude Sonnet.

```python
class QualityAgent:
    """Agent for assessing article quality."""

    async def analyze(self, article: Article) -> QualityAssessment
```

**Quality Dimensions:**
- **Source Credibility** (0-1): Reputation and reliability of source
- **Content Depth** (0-1): Thoroughness and detail of coverage
- **Writing Quality** (0-1): Clarity, structure, and professionalism
- **Factual Accuracy** (0-1): Accuracy and citation quality

**Output:**
```python
@dataclass
class QualityAssessment:
    overall_score: float  # 0-1
    source_credibility: float
    content_depth: float
    writing_quality: float
    factual_accuracy: float
    reasoning: str
```

### Bias Agent

Located at: `packages/core/src/agents/bias_agent.py`

The Bias Agent detects political bias in article content.

```python
class BiasAgent:
    """Agent for detecting political bias."""

    async def analyze(self, article: Article) -> BiasAssessment
```

**Bias Directions:**
- `left`: Strong progressive/liberal lean
- `center-left`: Moderate progressive lean
- `center`: Neutral/balanced coverage
- `center-right`: Moderate conservative lean
- `right`: Strong conservative lean

**Output:**
```python
@dataclass
class BiasAssessment:
    direction: str  # left, center-left, center, center-right, right
    confidence: float  # 0-1
    indicators: list[str]  # Specific bias indicators found
    reasoning: str
```

### Connection Agent

Located at: `packages/core/src/agents/connection_agent.py`

The Connection Agent finds relationships between articles.

```python
class ConnectionAgent:
    """Agent for finding article connections."""

    async def find_connections(
        self,
        articles: list[Article]
    ) -> list[Connection]
```

**Connection Types:**
- **same_topic**: Articles covering the same story
- **related_topic**: Articles with overlapping themes
- **thematic**: Articles connected by broader themes
- **causal**: Articles with cause-effect relationship

**Output:**
```python
@dataclass
class Connection:
    article1_id: str
    article2_id: str
    similarity: float  # 0-1
    connection_type: str
    description: str
```

## Orchestrator

Located at: `packages/core/src/orchestrator.py`

The Orchestrator coordinates all agents to generate digests.

```python
class Orchestrator:
    """Coordinates agents for digest generation."""

    async def generate_digest(
        self,
        topics: list[str],
        preferences: UserPreferences
    ) -> Digest
```

**Pipeline Stages:**
1. **Search**: Discover articles for each topic
2. **Fetch**: Retrieve full article content
3. **Parse**: Extract structured data
4. **Quality**: Assess article quality
5. **Filter**: Remove low-quality articles
6. **Bias**: Detect political bias
7. **Connect**: Find article relationships
8. **Generate**: Create final digest

**Events:**
The orchestrator emits events during processing:
```python
orchestrator.on("phase", callback)  # Phase started/completed
orchestrator.on("progress", callback)  # Progress updates
orchestrator.on("error", callback)  # Error occurred
orchestrator.on("complete", callback)  # Digest complete
```

## Configuration

### Provider Selection

```python
from core.providers import create_provider

# OpenRouter (default)
provider = create_provider("openrouter", api_key="...")

# Anthropic (fallback)
provider = create_provider("anthropic", api_key="...")
```

### Agent Configuration

```python
config = {
    "tier1_model": "deepseek/deepseek-v3.2",
    "tier2_model": "anthropic/claude-sonnet-4",
    "quality_threshold": 0.5,
    "max_articles_per_topic": 10,
}
```

## Testing

Run agent tests:
```bash
cd packages/core
uv run pytest tests/agents/ -v
```

Test coverage includes:
- Unit tests for each agent
- Mock provider tests
- Integration tests for orchestrator
- Edge case handling
