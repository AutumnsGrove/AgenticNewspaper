# MCP Subagent Architecture

**Version:** 2.0
**Date:** October 23, 2025
**Purpose:** Explains how Model Context Protocol (MCP) provides model flexibility for Agent SDK subagents

---

## Overview

This document explains the integration between **Claude Agent SDK** (orchestration layer) and **MCP servers** (model provider layer) in the Intelligent News Aggregator.

### Architecture Philosophy

**Agent SDK** = Orchestration & Coordination
**MCP** = Model Provider Abstraction

```
┌─────────────────────────────────────────────────────┐
│  Agent SDK Orchestrator (Claude Sonnet)             │
│  • Manages subagent lifecycle                       │
│  • Coordinates multi-agent workflows                │
│  • Handles context isolation                        │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ defines subagents
                   ↓
┌─────────────────────────────────────────────────────┐
│  Agent SDK Subagents                                │
│  • search_agent                                     │
│  • parser_agent                                     │
│  • analyzer_agent                                   │
│  • bias_detector                                    │
│  • synthesizer                                      │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ uses MCP tools
                   ↓
┌─────────────────────────────────────────────────────┐
│  MCP Tools Layer                                    │
│  • llm_complete(model, prompt, max_tokens)          │
│  • llm_stream(model, prompt)                        │
│  • get_cost(model, tokens)                          │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ routes to providers
                   ↓
┌─────────────────────────────────────────────────────┐
│  MCP Servers (Model Providers)                      │
│  • claude_mcp_server → Haiku/Sonnet                 │
│  • kimi_mcp_server → Kimi K2                        │
│  • openrouter_mcp_server → Any model                │
└─────────────────────────────────────────────────────┘
```

---

## Why This Architecture?

### Problem: Hardcoded Model Selection

**Bad approach:**
```python
# Direct API calls - hard to swap models
client = anthropic.Anthropic(api_key=key)
response = client.messages.create(
    model="claude-haiku-4-20250514",  # Hardcoded!
    max_tokens=2000,
    messages=[...]
)
```

**Issues:**
- ❌ Can't easily swap Haiku → Kimi K2
- ❌ Cost optimization requires code changes
- ❌ No fallback if provider has issues
- ❌ Can't compare models side-by-side

### Solution: MCP Abstraction Layer

**Good approach:**
```python
# MCP provides abstraction
response = await mcp_tools.llm_complete(
    provider="tier1_default",  # Configurable!
    prompt=prompt,
    max_tokens=2000
)
```

**Benefits:**
- ✅ Swap providers via config, no code changes
- ✅ Easy A/B testing (Claude vs. Kimi)
- ✅ Automatic fallback on failures
- ✅ Centralized cost tracking
- ✅ Provider-agnostic subagents

---

## Agent SDK + MCP Integration

### Orchestrator Setup

```python
# src/orchestrator/main_agent.py

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from mcp_servers import create_mcp_servers

async def create_orchestrator():
    """
    Create Agent SDK orchestrator with MCP-enabled subagents
    """

    # 1. Initialize MCP servers
    mcp_servers = create_mcp_servers()

    # 2. Define subagents (they will use MCP tools)
    subagents = {
        "search": SearchAgentDefinition(),
        "parser": ParserAgentDefinition(),
        "analyzer": AnalyzerAgentDefinition(),
        "bias_detector": BiasDetectorAgentDefinition(),
        "synthesizer": SynthesizerAgentDefinition(),
    }

    # 3. Configure Agent SDK orchestrator
    options = ClaudeAgentOptions(
        model="claude-sonnet-4-20250514",  # Orchestrator always Sonnet
        max_turns=50,
        agents=subagents,
        mcp_servers=mcp_servers,  # Subagents can access MCP tools
    )

    return ClaudeSDKClient(options)
```

### MCP Server Creation

```python
# src/mcp_servers/__init__.py

def create_mcp_servers():
    """
    Initialize all MCP servers based on configuration
    """
    config = load_mcp_config()  # Load from mcp_config.yaml
    secrets = load_secrets()

    servers = {}

    # Claude MCP Server (always enabled)
    if config["providers"]["claude_haiku"]["enabled"]:
        servers["claude_provider"] = ClaudeMCPServer(
            api_key=secrets["anthropic_api_key"],
            models={
                "haiku": "claude-haiku-4-20250514",
                "sonnet": "claude-sonnet-4-20250514",
            }
        )

    # Kimi K2 MCP Server (Phase 6+)
    if config["providers"]["kimi_k2"]["enabled"]:
        servers["kimi_provider"] = KimiMCPServer(
            api_key=secrets["kimi_api_key"]
        )

    # OpenRouter MCP Server (optional)
    if config["providers"].get("openrouter", {}).get("enabled"):
        servers["openrouter_provider"] = OpenRouterMCPServer(
            api_key=secrets["openrouter_api_key"]
        )

    return servers
```

---

## Subagent Definition with MCP Tools

### Example: Search Agent

```python
# src/agents/tier1_execution/search_agent.py

from claude_agent_sdk import AgentDefinition

class SearchAgentDefinition(AgentDefinition):
    """
    Search agent that uses MCP to call different LLM providers
    """

    def __init__(self):
        super().__init__(
            name="search",
            description="Searches for news articles on given topics",
            tools=[
                "web_search",      # MCP tool for Tavily/Brave
                "llm_complete",    # MCP tool for LLM calls
                "get_cost",        # MCP tool for cost tracking
            ],
            system_prompt="""
            You are a news search specialist. Your job is to find relevant
            articles for given topics.

            When you need LLM reasoning (e.g., to generate search queries),
            use the `llm_complete` tool with provider="tier1_default".

            This will automatically route to the configured Tier 1 provider
            (Haiku in Phase 1-5, optionally Kimi K2 in Phase 6).

            Workflow:
            1. Use llm_complete to generate optimized search queries
            2. Use web_search to find articles
            3. Return top 10-15 URLs with initial relevance scores

            Report back a summary to the orchestrator, not full content.
            """
        )

    async def run(self, task: str, context: dict):
        """
        This method is called by Agent SDK when orchestrator delegates a task
        """

        # Step 1: Generate search queries using MCP
        query_generation_prompt = f"""
        Generate 2-3 optimized search queries for this topic:
        {task}

        User preferences:
        {context['user_preferences']}

        Return JSON: {{"queries": ["query1", "query2", "query3"]}}
        """

        # Call LLM via MCP (automatically routes to tier1_default provider)
        query_response = await self.tools.llm_complete(
            provider="tier1_default",  # From mcp_config.yaml
            prompt=query_generation_prompt,
            max_tokens=500,
            temperature=0.3
        )

        queries = parse_json(query_response.content)

        # Step 2: Execute searches
        results = []
        for query in queries["queries"]:
            search_results = await self.tools.web_search(
                query=query,
                max_results=10
            )
            results.extend(search_results)

        # Step 3: Deduplicate and score
        deduplicated = deduplicate_urls(results)

        # Step 4: Use LLM to score initial relevance
        scoring_prompt = f"""
        Score these URLs for relevance to topic: {task}
        URLs: {deduplicated}
        Return JSON with scores 0-1.
        """

        scoring_response = await self.tools.llm_complete(
            provider="tier1_default",
            prompt=scoring_prompt,
            max_tokens=1000
        )

        scored_urls = parse_json(scoring_response.content)

        # Step 5: Track cost
        total_cost = (
            query_response.cost +
            scoring_response.cost
        )

        # Return summary to orchestrator
        return {
            "topic": task,
            "urls_found": len(scored_urls),
            "top_urls": scored_urls[:15],  # Top 15 only
            "cost": total_cost,
            "tokens_used": query_response.tokens + scoring_response.tokens,
        }
```

### Example: Analysis Agent

```python
# src/agents/tier2_reasoning/analysis_agent.py

class AnalysisAgentDefinition(AgentDefinition):
    """
    Analysis agent that uses MCP to call Sonnet for deep reasoning
    """

    def __init__(self):
        super().__init__(
            name="analyzer",
            description="Analyzes article quality and relevance",
            tools=[
                "llm_complete",
                "get_cost",
            ],
            system_prompt="""
            You are a content analysis specialist. You analyze news articles
            for quality and relevance.

            When you need LLM reasoning, use `llm_complete` with
            provider="tier2_default". This will use Sonnet, which is better
            for nuanced analysis.

            Analyze in HN comment style - technical, skeptical, focused on
            implications and "why this matters".

            Return:
            - relevance_score (0-1)
            - quality_score (0-1)
            - key_points (HN-style, 3-5 bullets)
            - implications (why this matters)
            - recommendation (include/exclude/investigate)
            """
        )

    async def run(self, article: dict, context: dict):
        """
        Analyze a single article
        """

        analysis_prompt = f"""
        Analyze this article for a technically sophisticated reader
        (think Hacker News audience).

        Article:
        Title: {article['title']}
        Source: {article['source']}
        Content: {article['content'][:5000]}  # First 5000 chars

        User interests:
        {context['user_topics']}

        Provide:
        1. Relevance score (0-1): How well does this match user interests?
        2. Quality score (0-1): How credible and substantial is this?
        3. Key points (3-5 bullets, HN style): What are the technical details?
        4. Implications: Why does this matter? What are the long-term effects?
        5. Recommendation: include/exclude/investigate

        Return JSON.
        """

        # Call Sonnet via MCP
        response = await self.tools.llm_complete(
            provider="tier2_default",  # Always Sonnet for Tier 2
            prompt=analysis_prompt,
            max_tokens=5000,
            temperature=0.2
        )

        analysis = parse_json(response.content)

        return {
            "article_id": article["id"],
            "relevance_score": analysis["relevance_score"],
            "quality_score": analysis["quality_score"],
            "key_points_hn_style": analysis["key_points"],
            "implications": analysis["implications"],
            "recommendation": analysis["recommendation"],
            "cost": response.cost,
            "tokens_used": response.tokens,
        }
```

---

## MCP Server Implementation

### Base Provider Interface

```python
# src/mcp_servers/base_provider.py

from abc import ABC, abstractmethod
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class LLMResponse:
    """Standard response format from any LLM provider"""
    content: str
    input_tokens: int
    output_tokens: int
    cost: float
    model: str
    provider: str

class BaseLLMProvider(ABC):
    """Base class for all LLM providers accessed via MCP"""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Complete a prompt and return standardized response
        """
        pass

    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """Count tokens in text using provider's tokenizer"""
        pass

    @abstractmethod
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is accessible"""
        pass
```

### Claude MCP Server

```python
# src/mcp_servers/claude_mcp_server.py

import anthropic
from .base_provider import BaseLLMProvider, LLMResponse

class ClaudeMCPServer(BaseLLMProvider):
    """MCP server for Claude models (Haiku and Sonnet)"""

    def __init__(self, api_key: str, models: dict):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.models = models  # {"haiku": "claude-haiku-4-...", "sonnet": "..."}

        # Pricing per million tokens
        self.pricing = {
            "claude-haiku-4-20250514": {
                "input": 0.25,
                "output": 1.25
            },
            "claude-sonnet-4-20250514": {
                "input": 3.0,
                "output": 15.0
            }
        }

    async def complete(
        self,
        prompt: str,
        max_tokens: int,
        model_variant: str = "haiku",  # "haiku" or "sonnet"
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Complete using specified Claude model variant
        """
        model = self.models[model_variant]

        response = await self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )

        cost = self.calculate_cost(
            response.usage.input_tokens,
            response.usage.output_tokens,
            model
        )

        return LLMResponse(
            content=response.content[0].text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost=cost,
            model=model,
            provider="claude"
        )

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = None
    ) -> float:
        pricing = self.pricing[model]
        return (
            (input_tokens / 1_000_000) * pricing["input"] +
            (output_tokens / 1_000_000) * pricing["output"]
        )

    def get_token_count(self, text: str) -> int:
        # Use Claude's token counter
        return self.client.count_tokens(text)

    async def health_check(self) -> bool:
        try:
            await self.complete("test", max_tokens=5)
            return True
        except Exception:
            return False
```

### Kimi K2 MCP Server

```python
# src/mcp_servers/kimi_mcp_server.py

import httpx
from .base_provider import BaseLLMProvider, LLMResponse

class KimiMCPServer(BaseLLMProvider):
    """MCP server for Kimi K2 model (cost optimization)"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "moonshot-v1-128k"
        self.base_url = "https://api.moonshot.cn/v1"

        # Much cheaper pricing!
        self.pricing = {
            "input": 0.05,   # $0.05 per MTok
            "output": 0.05   # $0.05 per MTok
        }

    async def complete(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Complete using Kimi K2
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    **kwargs
                },
                timeout=60.0
            )

            data = response.json()

            cost = self.calculate_cost(
                data["usage"]["prompt_tokens"],
                data["usage"]["completion_tokens"]
            )

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                input_tokens=data["usage"]["prompt_tokens"],
                output_tokens=data["usage"]["completion_tokens"],
                cost=cost,
                model=self.model,
                provider="kimi"
            )

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            (input_tokens / 1_000_000) * self.pricing["input"] +
            (output_tokens / 1_000_000) * self.pricing["output"]
        )

    def get_token_count(self, text: str) -> int:
        # Approximate token count (Kimi uses similar tokenizer to GPT)
        return len(text) // 4

    async def health_check(self) -> bool:
        try:
            await self.complete("test", max_tokens=5)
            return True
        except Exception:
            return False
```

---

## MCP Configuration

### Configuration File

```yaml
# src/mcp_servers/mcp_config.yaml

# ========================================
# MCP PROVIDERS
# ========================================

providers:
  # Claude (Primary)
  claude_haiku:
    class: ClaudeMCPServer
    model_variant: haiku
    enabled: true
    priority: 1  # Try first

  claude_sonnet:
    class: ClaudeMCPServer
    model_variant: sonnet
    enabled: true
    priority: 1

  # Kimi K2 (Phase 6 optimization)
  kimi_k2:
    class: KimiMCPServer
    enabled: false  # Enable in Phase 6
    priority: 2     # Fallback

  # OpenRouter (future)
  openrouter:
    class: OpenRouterMCPServer
    enabled: false
    priority: 3

# ========================================
# AGENT → PROVIDER MAPPING
# ========================================

agent_providers:
  # Tier 1 Execution Agents
  tier1_default:
    phase1_5: claude_haiku
    phase6_primary: kimi_k2
    phase6_fallback: claude_haiku

  # Tier 2 Reasoning Agents (always Sonnet)
  tier2_default:
    default: claude_sonnet
    fallback: null  # No fallback - reasoning needs quality

  # Tier 3 Advanced Agents (always Sonnet)
  tier3_default:
    default: claude_sonnet

# ========================================
# FAILOVER & RETRIES
# ========================================

failover:
  enabled: true
  max_retries: 3
  retry_delay_seconds: 2
  fallback_on_error: true

# ========================================
# COST TRACKING
# ========================================

cost_tracking:
  enabled: true
  log_all_calls: true
  database: data/cost_history.db
  alert_on_expensive_calls: true
  expensive_call_threshold_usd: 0.10
```

### Loading Configuration

```python
# src/mcp_servers/config_loader.py

import yaml
from pathlib import Path

def load_mcp_config():
    """Load MCP configuration from YAML"""
    config_path = Path(__file__).parent / "mcp_config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)

def get_provider_for_tier(tier: str, phase: int = 5) -> str:
    """
    Get the appropriate provider for a given tier and phase
    """
    config = load_mcp_config()
    tier_config = config["agent_providers"].get(tier)

    if not tier_config:
        raise ValueError(f"Unknown tier: {tier}")

    # Determine provider based on phase
    if phase >= 6 and "phase6_primary" in tier_config:
        return tier_config["phase6_primary"]
    elif phase >= 6 and "phase6_fallback" in tier_config:
        return tier_config["phase6_fallback"]
    else:
        return tier_config.get("default") or tier_config.get("phase1_5")
```

---

## Usage Examples

### Example 1: Calling LLM from Subagent

```python
# Inside a subagent's run() method

# Tier 1 agent calling default provider (Haiku or Kimi based on phase)
response = await self.tools.llm_complete(
    provider="tier1_default",
    prompt="Generate search queries for AI policy news",
    max_tokens=500
)

# Tier 2 agent calling Sonnet
response = await self.tools.llm_complete(
    provider="tier2_default",
    prompt="Analyze this article for bias",
    max_tokens=3000
)
```

### Example 2: Cost Tracking

```python
# Track cumulative costs across agents

cost_tracker = CostTracker()

# After each LLM call
cost_tracker.log_call(
    agent="search",
    provider="claude_haiku",
    input_tokens=1500,
    output_tokens=300,
    cost=0.00045
)

# Get daily summary
daily_cost = cost_tracker.get_daily_cost()
print(f"Today's cost: ${daily_cost:.2f}")

# Get breakdown by agent
breakdown = cost_tracker.get_cost_breakdown()
# {"search": $0.05, "analyzer": $0.30, "synthesizer": $0.03}
```

### Example 3: A/B Testing Providers

```python
# Run same task with both providers, compare results

task = "Summarize this article"

# Test with Claude Haiku
haiku_response = await mcp_tools.llm_complete(
    provider="claude_haiku",
    prompt=task,
    max_tokens=1000
)

# Test with Kimi K2
kimi_response = await mcp_tools.llm_complete(
    provider="kimi_k2",
    prompt=task,
    max_tokens=1000
)

# Compare
print(f"Haiku cost: ${haiku_response.cost:.4f}")
print(f"Kimi cost: ${kimi_response.cost:.4f}")
print(f"Cost savings: {(1 - kimi_response.cost/haiku_response.cost)*100:.1f}%")
print(f"\nQuality comparison:")
print(f"Haiku: {haiku_response.content}")
print(f"Kimi: {kimi_response.content}")
```

---

## Migration Path: Claude → Kimi K2

### Phase 1-5: All Claude

```yaml
agent_providers:
  tier1_default:
    default: claude_haiku

  tier2_default:
    default: claude_sonnet
```

Cost: **~$0.52/digest**

### Phase 6: Kimi K2 for Tier 1

```yaml
agent_providers:
  tier1_default:
    default: kimi_k2            # Just change this line!
    fallback: claude_haiku      # Failover if Kimi has issues

  tier2_default:
    default: claude_sonnet      # No change - keep quality
```

Cost: **~$0.50/digest** (4% savings)

**No code changes required** - just config update!

---

## Benefits Summary

| Aspect | Without MCP | With MCP |
|--------|------------|----------|
| **Model Swapping** | Code rewrite | Config change |
| **A/B Testing** | Duplicate code | Single line change |
| **Cost Tracking** | Manual | Automatic |
| **Failover** | Manual retry logic | Automatic |
| **Multi-Provider** | Hard to maintain | Easy |
| **Future-Proof** | Locked in | Open to new models |

---

**Document Version:** 2.0
**Last Updated:** October 23, 2025
