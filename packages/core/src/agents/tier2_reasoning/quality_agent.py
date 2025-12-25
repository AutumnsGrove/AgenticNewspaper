"""Quality Agent - Tier 2 reasoning agent for content quality analysis.

Evaluates article quality, relevance, and extracts key insights.
Uses LLM for intelligent analysis that goes beyond keyword matching.

Usage:
    from src.agents.tier2_reasoning import QualityAgent
    from src.providers import get_tier2_provider

    provider = get_tier2_provider()
    agent = QualityAgent(provider)

    analysis = await agent.analyze(article, topic_config)
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any

from ...models.article import (
    ParsedArticle,
    QualityAnalysis,
    ContentType,
)
from ...providers.base import BaseLLMProvider, LLMResponse


@dataclass
class TopicConfig:
    """Configuration for topic-based quality analysis."""

    name: str
    keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    min_quality: float = 0.5
    min_relevance: float = 0.5
    prefer_technical: bool = True
    max_age_days: int = 7


@dataclass
class QualityAgentStats:
    """Statistics for quality agent operations."""

    total_analyzed: int = 0
    passed_filter: int = 0
    failed_quality: int = 0
    failed_relevance: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0


# System prompt for quality analysis
QUALITY_SYSTEM_PROMPT = """You are an expert content analyst for a Hacker News-style news aggregator called "The Daily Clearing". Your role is to evaluate articles for quality, relevance, and newsworthiness.

You analyze content with the skeptical, technically-minded perspective of a HN reader:
- Prefer primary sources over press releases
- Value technical depth over marketing fluff
- Identify genuine novelty vs. incremental updates
- Detect hype vs. substance
- Appreciate clear, honest writing

For each article, you provide:
1. Quality scores (0.0-1.0) across multiple dimensions
2. Content classification
3. Key points that matter
4. Why this matters to a technical audience
5. Potential implications

Be brutally honest. Most content is mediocre - don't inflate scores. A 0.7+ should be genuinely good content.

IMPORTANT: Respond ONLY with valid JSON. No markdown, no explanations outside JSON."""


class QualityAgent:
    """
    Tier 2 Quality Analysis Agent.

    Evaluates articles for quality, relevance, and newsworthiness
    using LLM-powered analysis.
    """

    def __init__(
        self,
        provider: BaseLLMProvider,
        default_config: TopicConfig | None = None,
    ):
        """
        Initialize quality agent.

        Args:
            provider: LLM provider (Tier 2 recommended)
            default_config: Default topic configuration
        """
        self.provider = provider
        self.default_config = default_config or TopicConfig(name="General")
        self._stats = QualityAgentStats()

    async def analyze(
        self,
        article: ParsedArticle,
        topic_config: TopicConfig | None = None,
        user_interests: list[str] | None = None,
    ) -> QualityAnalysis:
        """
        Analyze article quality and relevance.

        Args:
            article: Parsed article to analyze
            topic_config: Topic-specific configuration
            user_interests: Additional user interest keywords

        Returns:
            QualityAnalysis with scores and insights
        """
        config = topic_config or self.default_config

        # Build analysis prompt
        prompt = self._build_analysis_prompt(article, config, user_interests)

        # Call LLM
        response = await self.provider.complete(
            prompt=prompt,
            max_tokens=1000,
            temperature=0.3,  # Low temperature for consistent scoring
            system_prompt=QUALITY_SYSTEM_PROMPT,
        )

        # Parse response
        analysis = self._parse_response(response, article, config)

        # Update stats
        self._stats.total_analyzed += 1
        self._stats.total_tokens += response.total_tokens
        self._stats.total_cost += response.cost_usd

        if analysis.should_include:
            self._stats.passed_filter += 1
        elif analysis.relevance_score < config.min_relevance:
            self._stats.failed_relevance += 1
        else:
            self._stats.failed_quality += 1

        return analysis

    def _build_analysis_prompt(
        self,
        article: ParsedArticle,
        config: TopicConfig,
        user_interests: list[str] | None,
    ) -> str:
        """Build the analysis prompt."""
        # Truncate content if too long
        content = article.content
        if len(content) > 6000:
            content = content[:6000] + "\n\n[Content truncated for analysis]"

        interests = ", ".join(user_interests) if user_interests else "general technology"

        prompt = f"""Analyze this article for quality and relevance.

TOPIC: {config.name}
KEYWORDS TO MATCH: {', '.join(config.keywords[:10])}
KEYWORDS TO AVOID: {', '.join(config.exclude_keywords[:5]) if config.exclude_keywords else 'none'}
USER INTERESTS: {interests}
TECHNICAL PREFERENCE: {'high' if config.prefer_technical else 'general audience'}

ARTICLE:
Title: {article.title}
Source: {article.source}
Author: {article.author or 'Unknown'}
Word Count: {article.word_count}
Published: {article.published_date.isoformat() if article.published_date else 'Unknown'}

Content:
{content}

Respond with JSON:
{{
    "relevance_score": 0.0-1.0,  // How relevant to topic/interests
    "quality_score": 0.0-1.0,    // Writing quality, depth, credibility
    "novelty_score": 0.0-1.0,    // How new/original is this
    "depth_score": 0.0-1.0,      // Technical/analytical depth
    "credibility_score": 0.0-1.0, // Source credibility, evidence quality
    "content_type": "news|opinion|analysis|research|press_release|blog|unknown",
    "technical_level": 1-5,       // 1=general, 5=expert
    "key_points": ["point1", "point2", "point3"],  // 3-5 key takeaways
    "why_matters": "One sentence on why this matters",
    "implications": ["implication1", "implication2"],  // Future implications
    "originality_indicators": ["indicator1"],  // What makes this original
    "skip_reason": null or "reason to skip",  // If should be filtered
    "should_include": true/false
}}"""

        return prompt

    def _parse_response(
        self,
        response: LLMResponse,
        article: ParsedArticle,
        config: TopicConfig,
    ) -> QualityAnalysis:
        """Parse LLM response into QualityAnalysis."""
        try:
            # Try to extract JSON from response
            content = response.content.strip()

            # Handle potential markdown code blocks
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\n?", "", content)
                content = re.sub(r"\n?```$", "", content)

            data = json.loads(content)

            # Parse content type
            content_type_str = data.get("content_type", "unknown").upper()
            try:
                content_type = ContentType[content_type_str]
            except KeyError:
                content_type = ContentType.UNKNOWN

            analysis = QualityAnalysis(
                relevance_score=self._clamp(data.get("relevance_score", 0.5)),
                quality_score=self._clamp(data.get("quality_score", 0.5)),
                novelty_score=self._clamp(data.get("novelty_score", 0.5)),
                depth_score=self._clamp(data.get("depth_score", 0.5)),
                credibility_score=self._clamp(data.get("credibility_score", 0.5)),
                content_type=content_type,
                key_points=data.get("key_points", [])[:5],
                technical_level=min(5, max(1, data.get("technical_level", 3))),
                originality_indicators=data.get("originality_indicators", []),
                why_matters=data.get("why_matters", ""),
                implications=data.get("implications", []),
                skip_reason=data.get("skip_reason"),
                should_include=data.get("should_include", True),
            )

            # Apply thresholds
            if analysis.relevance_score < config.min_relevance:
                analysis.should_include = False
                analysis.skip_reason = analysis.skip_reason or "Below relevance threshold"

            if analysis.quality_score < config.min_quality:
                analysis.should_include = False
                analysis.skip_reason = analysis.skip_reason or "Below quality threshold"

            return analysis

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Return default analysis on parse error
            return QualityAnalysis(
                relevance_score=0.5,
                quality_score=0.5,
                skip_reason=f"Analysis parse error: {str(e)}",
                should_include=True,  # Include on error, filter later
            )

    def _clamp(self, value: float) -> float:
        """Clamp value between 0 and 1."""
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.5

    async def batch_analyze(
        self,
        articles: list[ParsedArticle],
        topic_config: TopicConfig | None = None,
        user_interests: list[str] | None = None,
        max_concurrent: int = 5,
    ) -> list[QualityAnalysis]:
        """
        Analyze multiple articles concurrently.

        Args:
            articles: List of articles to analyze
            topic_config: Topic configuration
            user_interests: User interest keywords
            max_concurrent: Maximum concurrent analyses

        Returns:
            List of QualityAnalysis in same order as input
        """
        import asyncio

        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_with_limit(article: ParsedArticle) -> QualityAnalysis:
            async with semaphore:
                return await self.analyze(article, topic_config, user_interests)

        tasks = [analyze_with_limit(article) for article in articles]
        return await asyncio.gather(*tasks)

    async def quick_filter(
        self,
        article: ParsedArticle,
        config: TopicConfig,
    ) -> bool:
        """
        Quick relevance check without full analysis.

        Uses a simpler prompt for faster filtering.

        Args:
            article: Article to check
            config: Topic configuration

        Returns:
            True if article passes quick filter
        """
        prompt = f"""Quick relevance check. Is this article relevant to "{config.name}"?

Title: {article.title}
Source: {article.source}
Preview: {article.content[:500]}

Keywords to match: {', '.join(config.keywords[:5])}

Respond with ONLY "yes" or "no"."""

        response = await self.provider.complete(
            prompt=prompt,
            max_tokens=10,
            temperature=0.0,
        )

        return response.content.strip().lower() == "yes"

    def get_stats(self) -> dict[str, Any]:
        """Get agent statistics."""
        return {
            "agent": "QualityAgent",
            "tier": "2",
            "total_analyzed": self._stats.total_analyzed,
            "passed_filter": self._stats.passed_filter,
            "failed_quality": self._stats.failed_quality,
            "failed_relevance": self._stats.failed_relevance,
            "pass_rate": (
                self._stats.passed_filter / self._stats.total_analyzed * 100
                if self._stats.total_analyzed > 0
                else 0.0
            ),
            "total_tokens": self._stats.total_tokens,
            "total_cost_usd": self._stats.total_cost,
            "provider_stats": self.provider.get_stats(),
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = QualityAgentStats()
