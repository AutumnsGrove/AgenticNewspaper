"""Bias Agent - Tier 2 reasoning agent for bias detection and perspective analysis.

Detects bias in articles, identifies missing perspectives, and provides
skeptical analysis for balanced coverage.

Usage:
    from src.agents.tier2_reasoning import BiasAgent
    from src.providers import get_tier2_provider

    provider = get_tier2_provider()
    agent = BiasAgent(provider)

    analysis = await agent.analyze(article)
"""

import json
import re
from dataclasses import dataclass
from typing import Any

from ...models.article import (
    ParsedArticle,
    BiasAnalysis,
    BiasDirection,
)
from ...providers.base import BaseLLMProvider, LLMResponse


@dataclass
class BiasAgentStats:
    """Statistics for bias agent operations."""

    total_analyzed: int = 0
    highly_biased: int = 0
    neutral: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0


# System prompt for bias analysis
BIAS_SYSTEM_PROMPT = """You are an expert media analyst specializing in bias detection and critical analysis. Your role is to evaluate articles for potential bias, missing perspectives, and misleading content.

You analyze with intellectual honesty and nuance:
- Distinguish between inherent editorial perspective and problematic bias
- Identify loaded language without being overly sensitive
- Recognize when important context or perspectives are missing
- Detect potential misinformation or unsupported claims
- Provide constructive skepticism, not cynicism

Key principles:
1. All sources have some perspective - that's not automatically bias
2. Bias is about systematic distortion, not occasional word choice
3. Consider the source's stated mission and audience
4. Technical content can still have framing issues
5. Press releases and corporate blogs have inherent interests

For the "skeptic's corner": Write as a thoughtful HN commenter would - pointing out potential issues without being dismissive. Focus on substantive concerns, not nitpicking.

IMPORTANT: Respond ONLY with valid JSON. No markdown, no explanations outside JSON."""


class BiasAgent:
    """
    Tier 2 Bias Detection Agent.

    Analyzes articles for bias, identifies missing perspectives,
    and provides skeptical analysis.
    """

    def __init__(self, provider: BaseLLMProvider):
        """
        Initialize bias agent.

        Args:
            provider: LLM provider (Tier 2 recommended)
        """
        self.provider = provider
        self._stats = BiasAgentStats()

    async def analyze(
        self,
        article: ParsedArticle,
        context_articles: list[ParsedArticle] | None = None,
    ) -> BiasAnalysis:
        """
        Analyze article for bias and missing perspectives.

        Args:
            article: Article to analyze
            context_articles: Other articles on same topic for comparison

        Returns:
            BiasAnalysis with scores and insights
        """
        # Build analysis prompt
        prompt = self._build_analysis_prompt(article, context_articles)

        # Call LLM
        response = await self.provider.complete(
            prompt=prompt,
            max_tokens=1200,
            temperature=0.4,
            system_prompt=BIAS_SYSTEM_PROMPT,
        )

        # Parse response
        analysis = self._parse_response(response, article)

        # Update stats
        self._stats.total_analyzed += 1
        self._stats.total_tokens += response.total_tokens
        self._stats.total_cost += response.cost_usd

        if analysis.is_highly_biased:
            self._stats.highly_biased += 1
        elif analysis.bias_confidence > 0.5 and not analysis.is_highly_biased:
            self._stats.neutral += 1

        return analysis

    def _build_analysis_prompt(
        self,
        article: ParsedArticle,
        context_articles: list[ParsedArticle] | None,
    ) -> str:
        """Build the bias analysis prompt."""
        # Truncate content if too long
        content = article.content
        if len(content) > 5000:
            content = content[:5000] + "\n\n[Content truncated for analysis]"

        context_section = ""
        if context_articles:
            context_section = "\nOTHER ARTICLES ON SAME TOPIC (for comparison):\n"
            for i, ctx in enumerate(context_articles[:3], 1):
                context_section += f"{i}. {ctx.title} ({ctx.source}): {ctx.content[:200]}...\n"

        prompt = f"""Analyze this article for potential bias and missing perspectives.

ARTICLE:
Title: {article.title}
Source: {article.source}
Author: {article.author or 'Unknown'}
Published: {article.published_date.isoformat() if article.published_date else 'Unknown'}

Content:
{content}
{context_section}

Analyze for bias and respond with JSON:
{{
    "bias_score": 0.0-1.0,  // 0=far left, 0.5=neutral, 1.0=far right
    "bias_direction": "left|center_left|center|center_right|right|unknown",
    "bias_confidence": 0.0-1.0,  // How confident in bias assessment

    "loaded_language": ["phrase1", "phrase2"],  // Emotionally charged terms
    "framing_issues": ["issue1", "issue2"],  // How story is framed
    "missing_context": ["context1", "context2"],  // Important omissions
    "one_sided_sources": true/false,  // Are sources balanced?

    "missing_perspectives": ["perspective1", "perspective2"],  // Viewpoints not represented
    "suggested_counterpoints": ["point1", "point2"],  // Alternative views to consider

    "verifiable_claims": ["claim1", "claim2"],  // Claims that can be fact-checked
    "unverified_claims": ["claim1"],  // Claims without clear evidence
    "potentially_misleading": ["issue1"],  // Technically true but misleading statements

    "skeptics_corner": "A thoughtful 2-3 sentence skeptical take on this article",
    "red_flags": ["flag1", "flag2"]  // Specific concerns about this content
}}

Note: Be nuanced. A 0.5 bias score means balanced/neutral. Reserve extreme scores (< 0.2 or > 0.8) for clearly agenda-driven content. Technical/research content is often genuinely neutral."""

        return prompt

    def _parse_response(
        self,
        response: LLMResponse,
        article: ParsedArticle,
    ) -> BiasAnalysis:
        """Parse LLM response into BiasAnalysis."""
        try:
            # Try to extract JSON from response
            content = response.content.strip()

            # Handle potential markdown code blocks
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\n?", "", content)
                content = re.sub(r"\n?```$", "", content)

            data = json.loads(content)

            # Parse bias direction
            direction_str = data.get("bias_direction", "unknown").upper()
            try:
                bias_direction = BiasDirection[direction_str]
            except KeyError:
                bias_direction = BiasDirection.UNKNOWN

            return BiasAnalysis(
                bias_score=self._clamp(data.get("bias_score", 0.5)),
                bias_direction=bias_direction,
                bias_confidence=self._clamp(data.get("bias_confidence", 0.5)),
                loaded_language=data.get("loaded_language", [])[:10],
                framing_issues=data.get("framing_issues", [])[:5],
                missing_context=data.get("missing_context", [])[:5],
                one_sided_sources=data.get("one_sided_sources", False),
                missing_perspectives=data.get("missing_perspectives", [])[:5],
                suggested_counterpoints=data.get("suggested_counterpoints", [])[:5],
                verifiable_claims=data.get("verifiable_claims", [])[:5],
                unverified_claims=data.get("unverified_claims", [])[:5],
                potentially_misleading=data.get("potentially_misleading", [])[:3],
                skeptics_corner=data.get("skeptics_corner", ""),
                red_flags=data.get("red_flags", [])[:5],
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Return neutral analysis on parse error
            return BiasAnalysis(
                bias_score=0.5,
                bias_direction=BiasDirection.UNKNOWN,
                bias_confidence=0.0,
                skeptics_corner=f"Unable to complete bias analysis: {str(e)}",
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
        max_concurrent: int = 5,
    ) -> list[BiasAnalysis]:
        """
        Analyze multiple articles concurrently.

        Args:
            articles: List of articles to analyze
            max_concurrent: Maximum concurrent analyses

        Returns:
            List of BiasAnalysis in same order as input
        """
        import asyncio

        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_with_limit(article: ParsedArticle) -> BiasAnalysis:
            async with semaphore:
                return await self.analyze(article)

        tasks = [analyze_with_limit(article) for article in articles]
        return await asyncio.gather(*tasks)

    async def compare_coverage(
        self,
        articles: list[ParsedArticle],
        topic: str,
    ) -> dict[str, Any]:
        """
        Compare bias across multiple articles on the same topic.

        Args:
            articles: Articles covering the same story/topic
            topic: Topic name for context

        Returns:
            Comparison analysis
        """
        if len(articles) < 2:
            return {"error": "Need at least 2 articles to compare"}

        # Analyze each article
        analyses = await self.batch_analyze(articles)

        # Calculate aggregate stats
        avg_bias = sum(a.bias_score for a in analyses) / len(analyses)
        bias_range = max(a.bias_score for a in analyses) - min(a.bias_score for a in analyses)

        # Collect all missing perspectives
        all_missing = set()
        for analysis in analyses:
            all_missing.update(analysis.missing_perspectives)

        # Find common red flags
        flag_counts: dict[str, int] = {}
        for analysis in analyses:
            for flag in analysis.red_flags:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1
        common_flags = [f for f, c in flag_counts.items() if c > 1]

        return {
            "topic": topic,
            "article_count": len(articles),
            "average_bias_score": avg_bias,
            "bias_range": bias_range,
            "bias_distribution": {
                "left": sum(1 for a in analyses if a.bias_score < 0.4),
                "center": sum(1 for a in analyses if 0.4 <= a.bias_score <= 0.6),
                "right": sum(1 for a in analyses if a.bias_score > 0.6),
            },
            "missing_perspectives_across_all": list(all_missing),
            "common_red_flags": common_flags,
            "highly_biased_count": sum(1 for a in analyses if a.is_highly_biased),
        }

    async def generate_balanced_summary(
        self,
        article: ParsedArticle,
        bias_analysis: BiasAnalysis,
    ) -> str:
        """
        Generate a balanced summary that addresses bias concerns.

        Args:
            article: Original article
            bias_analysis: Previous bias analysis

        Returns:
            Balanced summary text
        """
        if not bias_analysis.is_highly_biased and not bias_analysis.missing_perspectives:
            # Article is balanced enough
            return ""

        prompt = f"""Given this potentially biased article, write a balanced 2-3 sentence summary that:
1. Presents the core facts neutrally
2. Notes important missing perspectives
3. Avoids loaded language

Article: {article.title}
Original content (excerpt): {article.content[:1000]}

Issues identified:
- Loaded language: {', '.join(bias_analysis.loaded_language[:3])}
- Missing perspectives: {', '.join(bias_analysis.missing_perspectives[:3])}
- Missing context: {', '.join(bias_analysis.missing_context[:3])}

Write a balanced summary:"""

        response = await self.provider.complete(
            prompt=prompt,
            max_tokens=200,
            temperature=0.3,
        )

        return response.content.strip()

    def get_stats(self) -> dict[str, Any]:
        """Get agent statistics."""
        return {
            "agent": "BiasAgent",
            "tier": "2",
            "total_analyzed": self._stats.total_analyzed,
            "highly_biased": self._stats.highly_biased,
            "neutral": self._stats.neutral,
            "high_bias_rate": (
                self._stats.highly_biased / self._stats.total_analyzed * 100
                if self._stats.total_analyzed > 0
                else 0.0
            ),
            "total_tokens": self._stats.total_tokens,
            "total_cost_usd": self._stats.total_cost,
            "provider_stats": self.provider.get_stats(),
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = BiasAgentStats()
