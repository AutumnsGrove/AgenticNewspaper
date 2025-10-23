# Intelligent News Aggregator - Quick Start Implementation

This document shows concrete code examples for implementing the agent-based news aggregator.

---

## 📁 Project Setup

```bash
# Initialize project
uv init intelligent-news-aggregator
cd intelligent-news-aggregator

# Add dependencies
uv add anthropic-claude-sdk
uv add tavily-python
uv add pyyaml
uv add python-dateutil
uv add omniparser  # Your existing parser

# Create structure
mkdir -p src/agents/{tier1_execution,tier2_reasoning,tier3_advanced}
mkdir -p src/{tools,models,orchestrator,utils}
mkdir -p config outputs/{daily_digests,archives}
mkdir -p tests/{unit,integration,fixtures}
```

---

## 🔧 Configuration Files

### config/user_preferences.yaml

```yaml
# User's news preferences
topics:
  - name: "Artificial Intelligence"
    keywords:
      - "AI"
      - "machine learning"
      - "LLM"
      - "neural networks"
    priority: 10
    min_articles: 3
    max_articles: 8

  - name: "Technology Policy"
    keywords:
      - "tech regulation"
      - "privacy"
      - "antitrust"
    priority: 8
    min_articles: 2
    max_articles: 5

  - name: "Climate Tech"
    keywords:
      - "clean energy"
      - "carbon capture"
      - "climate technology"
    priority: 7
    min_articles: 1
    max_articles: 3

sources:
  preferred:
    - "nytimes.com"
    - "reuters.com"
    - "techcrunch.com"
    - "arstechnica.com"
    - "nature.com"
    - "arxiv.org"
  
  excluded:
    - "tabloid-site.com"

output:
  format: "markdown"
  max_articles_per_digest: 15
  target_reading_time_minutes: 15
  include_summaries: true
  include_bias_notes: true
  obsidian_compatible: true

schedule:
  frequency: "daily"
  time: "06:00"
  timezone: "America/New_York"
```

### config/agent_configs.yaml

```yaml
# Agent model configurations
models:
  orchestrator: "claude-sonnet-4-20250514"
  tier1_execution: "claude-haiku-4-20250514"
  tier2_reasoning: "claude-sonnet-4-20250514"
  tier3_advanced: "claude-sonnet-4-20250514"

token_budgets:
  orchestrator: 20000
  search_agent: 2000
  fetch_agent: 1000
  parser_agent: 1500
  validation_agent: 1000
  analysis_agent: 5000
  bias_agent: 3000
  synthesis_agent: 10000
  research_agent: 15000

limits:
  daily_token_limit: 100000
  max_concurrent_agents: 5
  request_timeout_seconds: 60
```

---

## 💻 Core Implementation

### src/models/article.py

```python
"""Data models for articles and digests."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
import json

@dataclass
class ParsedArticle:
    """Represents a parsed article."""
    article_id: str
    url: str
    title: str
    content: str
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    source: str = ""
    word_count: int = 0
    format: str = "html"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AnalysisResult:
    """Results from content analysis."""
    article_id: str
    relevance_score: float  # 0.0-1.0
    quality_score: float    # 0.0-1.0
    bias_score: float       # 0.0-1.0
    key_points: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    verified_claims: int = 0
    unverified_claims: int = 0
    recommendation: str = "exclude"  # include, exclude, investigate
    reasoning: str = ""

@dataclass
class AnalyzedArticle:
    """Article with analysis results."""
    article: ParsedArticle
    analysis: AnalysisResult

@dataclass
class TokenUsage:
    """Token usage tracking."""
    orchestrator: int = 0
    search_agents: int = 0
    parser_agents: int = 0
    analysis_agents: int = 0
    synthesis_agent: int = 0
    
    @property
    def total(self) -> int:
        return (self.orchestrator + self.search_agents + 
                self.parser_agents + self.analysis_agents + 
                self.synthesis_agent)

@dataclass
class DigestMetadata:
    """Metadata about the digest generation."""
    total_articles_analyzed: int
    articles_included: int
    sources_used: List[str]
    token_usage: TokenUsage
    processing_time_seconds: float
    generation_date: datetime = field(default_factory=datetime.now)

@dataclass
class DailyDigest:
    """Complete daily news digest."""
    date: datetime
    articles: List[AnalyzedArticle]
    topics: Dict[str, List[AnalyzedArticle]]
    summary: str
    metadata: DigestMetadata
    markdown_content: str
    
    def save(self, filepath: str):
        """Save digest to file."""
        with open(filepath, 'w') as f:
            f.write(self.markdown_content)
```

---

### src/tools/web_tools.py

```python
"""MCP tools for web search and fetching."""

from anthropic_claude_sdk import tool, create_sdk_mcp_server
from tavily import TavilyClient
import httpx
from typing import List, Dict, Any

# Initialize Tavily client
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

@tool(
    name="web_search",
    description="Search the web for news articles on a given topic",
    input_schema={
        "query": str,
        "time_range": str,  # "day", "week", "month"
        "max_results": int,
        "domains": list[str]  # optional domain filter
    }
)
async def web_search(
    query: str,
    time_range: str = "day",
    max_results: int = 10,
    domains: list = None
) -> Dict[str, Any]:
    """
    Search for news articles using Tavily.
    Returns URLs, titles, snippets, and metadata.
    """
    search_params = {
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "topic": "news",
        "days": 1 if time_range == "day" else 7 if time_range == "week" else 30
    }
    
    if domains:
        search_params["include_domains"] = domains
    
    try:
        results = tavily.search(**search_params)
        
        return {
            "success": True,
            "results": [
                {
                    "url": r["url"],
                    "title": r["title"],
                    "snippet": r["content"][:200],
                    "score": r["score"],
                    "published_date": r.get("published_date")
                }
                for r in results.get("results", [])
            ],
            "query": query,
            "total_found": len(results.get("results", []))
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": []
        }

@tool(
    name="fetch_url",
    description="Fetch the full content of a web page",
    input_schema={
        "url": str,
        "timeout": int
    }
)
async def fetch_url(url: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Fetch content from a URL.
    Returns raw HTML/text content.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            
            return {
                "success": True,
                "url": url,
                "content": response.text,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "content_length": len(response.text)
            }
    except Exception as e:
        return {
            "success": False,
            "url": url,
            "error": str(e)
        }

# Create MCP server with these tools
def create_web_tools_server():
    """Create MCP server for web tools."""
    return create_sdk_mcp_server(
        name="web_tools",
        version="1.0.0",
        tools=[web_search, fetch_url]
    )
```

---

### src/tools/parser_tools.py

```python
"""MCP tools for parsing content with OmniParser."""

from anthropic_claude_sdk import tool, create_sdk_mcp_server
from omniparser import parse_document
import tempfile
import hashlib
from typing import Dict, Any

@tool(
    name="parse_content",
    description="Parse content using OmniParser (handles HTML, PDF, DOCX, etc.)",
    input_schema={
        "content": str,
        "url": str,
        "content_type": str
    }
)
async def parse_content(
    content: str,
    url: str,
    content_type: str = "text/html"
) -> Dict[str, Any]:
    """
    Parse content using OmniParser.
    Handles format detection and extraction.
    """
    try:
        # Create temp file for OmniParser
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        # Parse with OmniParser
        doc = parse_document(
            temp_path,
            options={
                "extract_images": False,
                "clean_text": True,
                "detect_chapters": False
            }
        )
        
        # Extract article info
        return {
            "success": True,
            "url": url,
            "title": doc.metadata.title or "Untitled",
            "author": doc.metadata.author,
            "content": doc.content,
            "word_count": doc.word_count,
            "published_date": doc.metadata.publication_date,
            "format": doc.metadata.original_format
        }
        
    except Exception as e:
        return {
            "success": False,
            "url": url,
            "error": str(e)
        }

@tool(
    name="detect_format",
    description="Detect the format of content (HTML, PDF, etc.)",
    input_schema={
        "content": str,
        "content_type": str,
        "url": str
    }
)
async def detect_format(
    content: str,
    content_type: str,
    url: str
) -> Dict[str, Any]:
    """Detect content format for routing to appropriate parser."""
    
    # Simple format detection based on content_type and content
    if "pdf" in content_type.lower():
        return {"format": "pdf", "confidence": 1.0}
    elif "html" in content_type.lower():
        return {"format": "html", "confidence": 1.0}
    elif content.strip().startswith("%PDF"):
        return {"format": "pdf", "confidence": 0.95}
    elif "<html" in content.lower()[:100]:
        return {"format": "html", "confidence": 0.95}
    else:
        return {"format": "text", "confidence": 0.5}

def create_parser_tools_server():
    """Create MCP server for parser tools."""
    return create_sdk_mcp_server(
        name="parser_tools",
        version="1.0.0",
        tools=[parse_content, detect_format]
    )
```

---

### src/agents/tier1_execution/search_agent.py

```python
"""Search agent - finds articles on given topics (Haiku)."""

from anthropic_claude_sdk import ClaudeSDKClient, ClaudeAgentOptions, AgentDefinition
from typing import List, Dict, Any

class SearchAgent:
    """Fast article search using Haiku."""
    
    @property
    def definition(self) -> AgentDefinition:
        """Agent definition for subagent use."""
        return AgentDefinition(
            description="Search for news articles on a given topic. Returns URLs and metadata.",
            prompt="""
            You are a search specialist. Your job is to find high-quality news articles.
            
            Given a topic, you should:
            1. Generate an effective search query
            2. Use the web_search tool with appropriate time range
            3. Filter results by relevance
            4. Return a structured list of promising URLs
            
            Be efficient - you have a 2000 token budget.
            Return results in this JSON format:
            {
              "topic": "...",
              "urls": [{"url": "...", "title": "...", "relevance": 0.0-1.0}],
              "total_found": N
            }
            """,
            tools=["web_search"],
            model="claude-haiku-4-20250514"
        )
    
    async def search_topic(
        self,
        topic: str,
        keywords: List[str],
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Search for articles on a topic.
        
        Args:
            topic: Topic name
            keywords: List of keywords for this topic
            preferences: User's source preferences
            
        Returns:
            Dict with search results
        """
        options = ClaudeAgentOptions(
            model="claude-haiku-4-20250514",
            max_turns=5,
            # Tools would be added via MCP servers
        )
        
        async with ClaudeSDKClient(options) as client:
            # Build prompt with user preferences
            preferred_sources = preferences.get("preferred_sources", [])
            excluded_sources = preferences.get("excluded_sources", [])
            
            await client.connect(f"""
            Search for news articles about: {topic}
            
            Keywords to use: {', '.join(keywords)}
            
            Preferences:
            - Preferred sources: {', '.join(preferred_sources)}
            - Excluded sources: {', '.join(excluded_sources)}
            - Time range: last 24 hours
            - Focus on: high-quality, recent, authoritative sources
            
            Use web_search tool to find 10-15 articles.
            Evaluate each for relevance to the topic.
            Return results as JSON.
            """)
            
            # Get response
            result = await client.receive_response()
            
            # Parse and return
            return self._extract_search_results(result)
    
    def _extract_search_results(self, result) -> Dict[str, Any]:
        """Extract structured results from agent response."""
        # Implementation would parse the agent's JSON response
        pass
```

---

### src/agents/tier2_reasoning/analysis_agent.py

```python
"""Content analysis agent - evaluates quality and relevance (Sonnet)."""

from anthropic_claude_sdk import ClaudeSDKClient, ClaudeAgentOptions, AgentDefinition
from typing import Dict, Any
from ...models.article import ParsedArticle, AnalysisResult

class AnalysisAgent:
    """Deep content analysis using Sonnet reasoning."""
    
    @property
    def definition(self) -> AgentDefinition:
        """Agent definition for subagent use."""
        return AgentDefinition(
            description="Analyze article quality, relevance, and credibility",
            prompt="""
            You are a content analyst. Evaluate articles for quality and relevance.
            
            Your analysis should assess:
            1. Relevance to user's stated interests (0.0-1.0 score)
            2. Overall quality (sourcing, evidence, writing) (0.0-1.0 score)
            3. Source credibility
            4. Key claims and supporting evidence
            5. Whether this is news-worthy for the user
            
            Consider:
            - Is the information new and significant?
            - Are claims backed by evidence?
            - Is the source authoritative?
            - Would the user find this valuable?
            
            Return structured JSON with your assessment.
            """,
            model="claude-sonnet-4-20250514"
        )
    
    async def analyze_article(
        self,
        article: ParsedArticle,
        user_interests: List[str]
    ) -> AnalysisResult:
        """
        Analyze an article's quality and relevance.
        
        Args:
            article: The parsed article
            user_interests: User's topics of interest
            
        Returns:
            Analysis result with scores and recommendations
        """
        options = ClaudeAgentOptions(
            model="claude-sonnet-4-20250514",
            max_turns=10,
            max_thinking_tokens=5000
        )
        
        async with ClaudeSDKClient(options) as client:
            await client.connect(f"""
            Analyze this article for quality and relevance:
            
            Title: {article.title}
            Source: {article.source}
            Author: {article.author or "Unknown"}
            Published: {article.published_date or "Unknown"}
            Word Count: {article.word_count}
            
            Content preview (first 1000 chars):
            {article.content[:1000]}
            
            User's interests: {', '.join(user_interests)}
            
            Evaluate:
            1. How relevant is this to the user's interests? (0.0-1.0)
            2. What is the quality of this article? (0.0-1.0)
            3. What are 3-5 key points?
            4. Any concerns about credibility or bias?
            5. Recommendation: include, exclude, or investigate further?
            
            Return your analysis as JSON:
            {{
              "relevance_score": 0.0-1.0,
              "quality_score": 0.0-1.0,
              "key_points": ["...", "..."],
              "concerns": ["..."],
              "recommendation": "include|exclude|investigate",
              "reasoning": "Brief explanation"
            }}
            """)
            
            result = await client.receive_response()
            return self._extract_analysis(result, article.article_id)
    
    def _extract_analysis(self, result, article_id: str) -> AnalysisResult:
        """Extract analysis from agent response."""
        # Parse JSON response and create AnalysisResult
        pass
```

---

### src/orchestrator/main_agent.py

```python
"""Main orchestrator agent - coordinates all subagents (Sonnet)."""

from anthropic_claude_sdk import ClaudeSDKClient, ClaudeAgentOptions
from typing import Dict, Any
import yaml
from datetime import datetime

from ..models.article import DailyDigest, DigestMetadata, TokenUsage
from ..tools.web_tools import create_web_tools_server
from ..tools.parser_tools import create_parser_tools_server
from ..agents.tier1_execution.search_agent import SearchAgent
from ..agents.tier2_reasoning.analysis_agent import AnalysisAgent

class MainOrchestratorAgent:
    """Main Sonnet agent that coordinates the entire pipeline."""
    
    def __init__(self, preferences_path: str, config_path: str):
        """Initialize orchestrator with config."""
        with open(preferences_path) as f:
            self.preferences = yaml.safe_load(f)
        
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        # Initialize subagents
        self.search_agent = SearchAgent()
        self.analysis_agent = AnalysisAgent()
        # ... other agents
    
    async def generate_daily_digest(self) -> DailyDigest:
        """
        Generate today's news digest.
        
        This is the main orchestration method that coordinates
        all subagents to produce the final digest.
        """
        start_time = datetime.now()
        
        # Prepare agent options with subagents
        options = ClaudeAgentOptions(
            model="claude-sonnet-4-20250514",
            max_turns=50,
            agents={
                "search": self.search_agent.definition,
                "analysis": self.analysis_agent.definition,
                # ... other agent definitions
            },
            mcp_servers={
                "web_tools": create_web_tools_server(),
                "parser_tools": create_parser_tools_server(),
            }
        )
        
        # Start main orchestration session
        async with ClaudeSDKClient(options) as client:
            await client.connect(f"""
            Generate today's personalized news digest.
            
            User Preferences:
            {yaml.dump(self.preferences)}
            
            Orchestration Plan:
            
            Phase 1: SEARCH
            For each topic in user preferences:
            - Use 'search' subagent to find articles
            - Get back summary of URLs found (not full content!)
            - Track token usage
            
            Phase 2: FETCH & PARSE
            For each promising URL from search:
            - Use parser_tools MCP server to fetch and parse
            - Get back article metadata and summary (not full content!)
            - Validate article quality
            
            Phase 3: ANALYZE
            For articles that pass initial filter:
            - Use 'analysis' subagent for deep evaluation
            - Get back scores and key points (not full content!)
            - Decide which to include in final digest
            
            Phase 4: SYNTHESIZE
            For included articles:
            - Group by topic
            - Create summaries
            - Format as markdown
            - Add metadata
            
            IMPORTANT for token efficiency:
            - Your context should only contain SUMMARIES from subagents
            - Do NOT hold full article content in your context
            - Each subagent works with full content in ITS context
            - You coordinate based on summaries
            
            Target:
            - 12-15 high-quality articles
            - Reading time: ~15 minutes
            - Token budget: 50,000 total across all agents
            
            Return the complete markdown digest.
            """)
            
            # Collect result
            messages = []
            async for message in client.receive_messages():
                messages.append(message)
                
                # Monitor progress
                if message.type == "assistant":
                    for block in message.content:
                        if block.type == "thinking":
                            print(f"Orchestrator thinking: {block.text[:100]}...")
                        elif block.type == "tool_use":
                            print(f"Orchestrator using: {block.name}")
            
            # Extract final digest
            digest_content = self._extract_digest_content(messages)
            
            # Create digest object
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            metadata = DigestMetadata(
                total_articles_analyzed=0,  # TODO: extract from messages
                articles_included=0,
                sources_used=[],
                token_usage=TokenUsage(),  # TODO: extract from messages
                processing_time_seconds=processing_time
            )
            
            digest = DailyDigest(
                date=datetime.now(),
                articles=[],
                topics={},
                summary="",
                metadata=metadata,
                markdown_content=digest_content
            )
            
            return digest
    
    def _extract_digest_content(self, messages) -> str:
        """Extract markdown content from agent messages."""
        # Find the final text response with the digest
        for message in reversed(messages):
            if message.type == "assistant":
                for block in message.content:
                    if block.type == "text":
                        return block.text
        return ""
```

---

### src/main.py

```python
"""Main entry point for news aggregator."""

import asyncio
from datetime import datetime
from orchestrator.main_agent import MainOrchestratorAgent

async def main():
    """Run daily news digest generation."""
    print("🗞️  Intelligent News Aggregator Starting...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    # Initialize orchestrator
    orchestrator = MainOrchestratorAgent(
        preferences_path="config/user_preferences.yaml",
        config_path="config/agent_configs.yaml"
    )
    
    # Generate digest
    print("🤖 Orchestrating agents...")
    digest = await orchestrator.generate_daily_digest()
    
    # Save output
    output_path = f"outputs/daily_digests/{datetime.now().strftime('%Y-%m-%d')}.md"
    digest.save(output_path)
    
    print()
    print("✅ Digest generated successfully!")
    print(f"📄 Saved to: {output_path}")
    print(f"📊 Stats:")
    print(f"   - Articles analyzed: {digest.metadata.total_articles_analyzed}")
    print(f"   - Articles included: {digest.metadata.articles_included}")
    print(f"   - Processing time: {digest.metadata.processing_time_seconds:.1f}s")
    print(f"   - Total tokens: {digest.metadata.token_usage.total:,}")
    print(f"   - Estimated cost: ${digest.metadata.token_usage.total / 1_000_000 * 3:.2f}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🚀 Running the System

### First Run

```bash
# 1. Setup environment
cp .env.example .env
# Add your API keys to .env:
# ANTHROPIC_API_KEY=sk-...
# TAVILY_API_KEY=tvly-...

# 2. Edit preferences
vim config/user_preferences.yaml
# Configure your topics and sources

# 3. Run
uv run python src/main.py
```

### Expected Output

```
🗞️  Intelligent News Aggregator Starting...
📅 Date: 2025-10-17 06:00

🤖 Orchestrating agents...
Orchestrator thinking: Reading user preferences, I see 3 main topics...
Orchestrator using: search
Orchestrator thinking: Search agent found 12 URLs for AI topic...
Orchestrator using: parse_content
Orchestrator thinking: Parser extracted 'EU AI Regulation' article...
Orchestrator using: analysis
Orchestrator thinking: Analysis shows high relevance (0.92), including...

✅ Digest generated successfully!
📄 Saved to: outputs/daily_digests/2025-10-17.md
📊 Stats:
   - Articles analyzed: 45
   - Articles included: 12
   - Processing time: 47.3s
   - Total tokens: 46,800
   - Estimated cost: $0.44
```

---

## 📅 Scheduling

### Using Cron (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add daily run at 6 AM
0 6 * * * cd /path/to/intelligent-news-aggregator && /path/to/uv run python src/main.py >> logs/cron.log 2>&1
```

### Using Systemd Timer (Linux)

```ini
# ~/.config/systemd/user/news-aggregator.service
[Unit]
Description=Intelligent News Aggregator

[Service]
Type=oneshot
WorkingDirectory=/path/to/intelligent-news-aggregator
ExecStart=/path/to/uv run python src/main.py

[Install]
WantedBy=default.target
```

```ini
# ~/.config/systemd/user/news-aggregator.timer
[Unit]
Description=Run news aggregator daily

[Timer]
OnCalendar=daily
OnCalendar=06:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
# Enable and start
systemctl --user enable news-aggregator.timer
systemctl --user start news-aggregator.timer

# Check status
systemctl --user status news-aggregator.timer
```

---

## 🧪 Testing

### Unit Test Example

```python
# tests/unit/test_search_agent.py

import pytest
from src.agents.tier1_execution.search_agent import SearchAgent

@pytest.mark.asyncio
async def test_search_agent_returns_urls():
    """Test that search agent returns structured results."""
    agent = SearchAgent()
    
    result = await agent.search_topic(
        topic="AI regulation",
        keywords=["AI", "regulation", "policy"],
        preferences={"preferred_sources": [], "excluded_sources": []}
    )
    
    assert result["success"] == True
    assert len(result["urls"]) > 0
    assert all("url" in item for item in result["urls"])
```

### Integration Test Example

```python
# tests/integration/test_full_pipeline.py

import pytest
from src.orchestrator.main_agent import MainOrchestratorAgent

@pytest.mark.asyncio
async def test_full_digest_generation():
    """Test end-to-end digest generation."""
    orchestrator = MainOrchestratorAgent(
        preferences_path="tests/fixtures/test_preferences.yaml",
        config_path="config/agent_configs.yaml"
    )
    
    digest = await orchestrator.generate_daily_digest()
    
    assert digest is not None
    assert digest.metadata.articles_included > 0
    assert len(digest.markdown_content) > 0
    assert digest.metadata.token_usage.total < 100000  # Under budget
```

---

## 📊 Monitoring Token Usage

### Add Logging

```python
# src/utils/metrics.py

import json
from datetime import datetime
from pathlib import Path

class MetricsLogger:
    """Log token usage and performance metrics."""
    
    def __init__(self, log_path: str = "outputs/metrics.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(exist_ok=True)
    
    def log_digest(self, digest):
        """Log digest generation metrics."""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "date": digest.date.isoformat(),
            "articles_analyzed": digest.metadata.total_articles_analyzed,
            "articles_included": digest.metadata.articles_included,
            "processing_time_seconds": digest.metadata.processing_time_seconds,
            "tokens": {
                "orchestrator": digest.metadata.token_usage.orchestrator,
                "search": digest.metadata.token_usage.search_agents,
                "parser": digest.metadata.token_usage.parser_agents,
                "analysis": digest.metadata.token_usage.analysis_agents,
                "synthesis": digest.metadata.token_usage.synthesis_agent,
                "total": digest.metadata.token_usage.total
            },
            "estimated_cost": digest.metadata.token_usage.total / 1_000_000 * 3
        }
        
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(metrics) + '\n')
```

### View Metrics

```python
# scripts/view_metrics.py

import json
import pandas as pd

# Load metrics
with open("outputs/metrics.jsonl") as f:
    metrics = [json.loads(line) for line in f]

# Create DataFrame
df = pd.DataFrame(metrics)

# Print summary
print(f"Total runs: {len(df)}")
print(f"Average tokens: {df['tokens'].apply(lambda x: x['total']).mean():.0f}")
print(f"Average cost: ${df['estimated_cost'].mean():.2f}")
print(f"Average time: {df['processing_time_seconds'].mean():.1f}s")

# Plot trends
import matplotlib.pyplot as plt

df['date'] = pd.to_datetime(df['date'])
df.set_index('date', inplace=True)
df['tokens'].apply(lambda x: x['total']).plot(title="Token Usage Over Time")
plt.ylabel("Tokens")
plt.show()
```

---

## 🎯 Next Steps

1. **Implement remaining agents**
   - Bias detection agent
   - Fact verification agent
   - Synthesis agent

2. **Add error handling**
   - Retry logic for failed fetches
   - Graceful degradation
   - Alert on repeated failures

3. **Optimize performance**
   - Parallel agent execution
   - Caching frequently accessed content
   - Rate limiting

4. **Enhance output**
   - HTML version
   - Email delivery
   - RSS feed generation

5. **User feedback loop**
   - Like/dislike articles
   - Adjust preferences based on feedback
   - Improve recommendations over time

---

This quick-start guide provides the foundation for building the intelligent news aggregator. The modular agent architecture makes it easy to add new capabilities and optimize individual components independently.
