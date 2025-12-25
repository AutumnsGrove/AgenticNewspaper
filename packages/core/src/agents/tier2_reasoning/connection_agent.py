"""Cross-Connection Agent - Tier 2 agent for finding relationships between articles.

Identifies thematic connections, contradictions, and patterns across
multiple articles to provide deeper insights.

Usage:
    from src.agents.tier2_reasoning import ConnectionAgent
    from src.providers import get_tier2_provider

    provider = get_tier2_provider()
    agent = ConnectionAgent(provider)

    connections = await agent.find_connections(articles)
"""

import json
import re
from dataclasses import dataclass
from typing import Any

from ...models.article import (
    ParsedArticle,
    AnalyzedArticle,
    CrossConnection,
)
from ...providers.base import BaseLLMProvider, LLMResponse


@dataclass
class ConnectionAgentStats:
    """Statistics for connection agent operations."""

    total_analyses: int = 0
    connections_found: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0


# System prompt for connection analysis
CONNECTION_SYSTEM_PROMPT = """You are an expert analyst who identifies meaningful connections between news articles. Your role is to find patterns, relationships, and insights that span multiple stories.

Types of connections to identify:
1. **Supports**: One article provides evidence/context for another
2. **Contradicts**: Articles present conflicting information or perspectives
3. **Extends**: One article builds on or deepens another's coverage
4. **Provides Context**: Background information that illuminates another story
5. **Pattern**: Multiple articles point to a broader trend

For HN-style analysis, focus on:
- Technical implications across stories
- Industry patterns and trends
- Cause-and-effect relationships
- Timeline connections (how events relate chronologically)
- Stakeholder overlaps (same companies, researchers, etc.)

Be selective - only identify connections that provide genuine insight. Not every article pair has a meaningful connection.

IMPORTANT: Respond ONLY with valid JSON. No markdown, no explanations outside JSON."""


class ConnectionAgent:
    """
    Tier 2 Cross-Connection Analysis Agent.

    Finds meaningful relationships between articles to provide
    deeper insights and pattern recognition.
    """

    def __init__(self, provider: BaseLLMProvider):
        """
        Initialize connection agent.

        Args:
            provider: LLM provider (Tier 2 recommended)
        """
        self.provider = provider
        self._stats = ConnectionAgentStats()

    async def find_connections(
        self,
        articles: list[ParsedArticle | AnalyzedArticle],
        min_strength: float = 0.5,
    ) -> list[tuple[str, str, CrossConnection]]:
        """
        Find connections between a set of articles.

        Args:
            articles: List of articles to analyze
            min_strength: Minimum connection strength to include

        Returns:
            List of (article1_id, article2_id, connection) tuples
        """
        if len(articles) < 2:
            return []

        # Extract ParsedArticle if given AnalyzedArticle
        parsed_articles = []
        for article in articles:
            if isinstance(article, AnalyzedArticle):
                parsed_articles.append(article.parsed_article)
            else:
                parsed_articles.append(article)

        # Build analysis prompt
        prompt = self._build_connection_prompt(parsed_articles)

        # Call LLM
        response = await self.provider.complete(
            prompt=prompt,
            max_tokens=1500,
            temperature=0.4,
            system_prompt=CONNECTION_SYSTEM_PROMPT,
        )

        # Parse response
        connections = self._parse_response(response, parsed_articles, min_strength)

        # Update stats
        self._stats.total_analyses += 1
        self._stats.connections_found += len(connections)
        self._stats.total_tokens += response.total_tokens
        self._stats.total_cost += response.cost_usd

        return connections

    def _build_connection_prompt(
        self,
        articles: list[ParsedArticle],
    ) -> str:
        """Build the connection analysis prompt."""
        articles_text = ""
        for i, article in enumerate(articles[:10]):  # Limit to 10 articles
            content_preview = article.content[:500] if len(article.content) > 500 else article.content
            articles_text += f"""
ARTICLE {i + 1}:
ID: {article.article_id}
Title: {article.title}
Source: {article.source}
Topic: {article.topic or 'General'}
Content: {content_preview}...
---
"""

        prompt = f"""Analyze these articles and identify meaningful connections between them.

{articles_text}

Find connections between article pairs. For each connection, provide:
1. The two article IDs involved
2. Type of connection (supports, contradicts, extends, provides_context, pattern)
3. Strength (0.0-1.0, where 1.0 is very strong)
4. Brief summary of the connection

Respond with JSON:
{{
    "connections": [
        {{
            "article1_id": "id1",
            "article2_id": "id2",
            "connection_type": "supports|contradicts|extends|provides_context|pattern",
            "strength": 0.0-1.0,
            "summary": "Brief explanation of how these articles connect"
        }}
    ],
    "patterns": [
        {{
            "pattern_name": "Name of the broader pattern",
            "article_ids": ["id1", "id2", "id3"],
            "description": "Description of the pattern across these articles"
        }}
    ],
    "cross_story_insight": "One key insight that emerges from looking across all these articles"
}}

Only include connections with strength >= 0.5. If no meaningful connections exist, return empty arrays."""

        return prompt

    def _parse_response(
        self,
        response: LLMResponse,
        articles: list[ParsedArticle],
        min_strength: float,
    ) -> list[tuple[str, str, CrossConnection]]:
        """Parse LLM response into connections."""
        try:
            # Try to extract JSON from response
            content = response.content.strip()

            # Handle potential markdown code blocks
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\n?", "", content)
                content = re.sub(r"\n?```$", "", content)

            data = json.loads(content)

            # Validate article IDs
            valid_ids = {a.article_id for a in articles}

            connections = []
            for conn_data in data.get("connections", []):
                article1_id = conn_data.get("article1_id", "")
                article2_id = conn_data.get("article2_id", "")
                strength = float(conn_data.get("strength", 0))

                # Validate
                if (
                    article1_id in valid_ids
                    and article2_id in valid_ids
                    and article1_id != article2_id
                    and strength >= min_strength
                ):
                    connection = CrossConnection(
                        related_article_id=article2_id,
                        connection_type=conn_data.get("connection_type", "related"),
                        connection_strength=min(1.0, max(0.0, strength)),
                        summary=conn_data.get("summary", ""),
                    )
                    connections.append((article1_id, article2_id, connection))

            return connections

        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return []

    async def generate_cross_story_summary(
        self,
        articles: list[ParsedArticle | AnalyzedArticle],
        topic: str | None = None,
    ) -> str:
        """
        Generate a synthesis paragraph about patterns across articles.

        Args:
            articles: Articles to synthesize
            topic: Optional topic for focus

        Returns:
            Cross-story summary text
        """
        if len(articles) < 2:
            return ""

        # Extract parsed articles
        parsed = []
        for article in articles[:8]:
            if isinstance(article, AnalyzedArticle):
                parsed.append(article.parsed_article)
            else:
                parsed.append(article)

        articles_text = "\n".join(
            f"- {a.title} ({a.source}): {a.content[:200]}..."
            for a in parsed
        )

        topic_context = f" about {topic}" if topic else ""

        prompt = f"""Based on these articles{topic_context}, write a brief (2-3 sentence) synthesis of the key patterns or insights that emerge from looking across all of them together.

Focus on:
- Trends that multiple articles point to
- Contradictions or debates in the field
- Bigger picture implications

Articles:
{articles_text}

Write a HN-style synthesis (technical, insightful, slightly skeptical):"""

        response = await self.provider.complete(
            prompt=prompt,
            max_tokens=200,
            temperature=0.5,
        )

        return response.content.strip()

    async def find_contradictions(
        self,
        articles: list[ParsedArticle],
    ) -> list[dict[str, Any]]:
        """
        Specifically find contradictions between articles.

        Args:
            articles: Articles to check for contradictions

        Returns:
            List of contradiction details
        """
        if len(articles) < 2:
            return []

        articles_text = "\n".join(
            f"[{i + 1}] {a.title}: {a.content[:400]}..."
            for i, a in enumerate(articles[:6])
        )

        prompt = f"""Identify any contradictions or conflicting claims between these articles.

{articles_text}

For each contradiction found, respond with JSON:
{{
    "contradictions": [
        {{
            "article_indices": [1, 3],
            "claim_1": "What article 1 claims",
            "claim_2": "What article 3 claims (contradicting)",
            "significance": "Why this contradiction matters",
            "possible_resolution": "How to reconcile or which might be more accurate"
        }}
    ]
}}

If no meaningful contradictions exist, return {{"contradictions": []}}"""

        response = await self.provider.complete(
            prompt=prompt,
            max_tokens=800,
            temperature=0.3,
        )

        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\n?", "", content)
                content = re.sub(r"\n?```$", "", content)
            data = json.loads(content)
            return data.get("contradictions", [])
        except (json.JSONDecodeError, TypeError):
            return []

    async def identify_trends(
        self,
        articles: list[ParsedArticle],
        topic: str,
    ) -> dict[str, Any]:
        """
        Identify broader trends from a collection of articles.

        Args:
            articles: Articles to analyze
            topic: Topic for context

        Returns:
            Trend analysis
        """
        articles_text = "\n".join(
            f"- {a.title} ({a.source}, {a.published_date.strftime('%Y-%m-%d') if a.published_date else 'unknown date'})"
            for a in articles[:10]
        )

        prompt = f"""Based on these recent articles about {topic}, identify emerging trends.

Articles:
{articles_text}

Respond with JSON:
{{
    "trends": [
        {{
            "trend_name": "Name of the trend",
            "description": "What's happening",
            "evidence": ["Article title 1", "Article title 2"],
            "direction": "growing|declining|stable|emerging",
            "confidence": 0.0-1.0
        }}
    ],
    "hot_topics": ["Topic 1", "Topic 2"],
    "fading_topics": ["Topic 3"],
    "prediction": "Brief prediction about where this topic is heading"
}}"""

        response = await self.provider.complete(
            prompt=prompt,
            max_tokens=600,
            temperature=0.5,
        )

        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\n?", "", content)
                content = re.sub(r"\n?```$", "", content)
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return {"trends": [], "hot_topics": [], "prediction": ""}

    def get_stats(self) -> dict[str, Any]:
        """Get agent statistics."""
        return {
            "agent": "ConnectionAgent",
            "tier": "2",
            "total_analyses": self._stats.total_analyses,
            "connections_found": self._stats.connections_found,
            "avg_connections_per_analysis": (
                self._stats.connections_found / self._stats.total_analyses
                if self._stats.total_analyses > 0
                else 0.0
            ),
            "total_tokens": self._stats.total_tokens,
            "total_cost_usd": self._stats.total_cost,
            "provider_stats": self.provider.get_stats(),
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = ConnectionAgentStats()
