"""Synthesis Agent - Tier 2 reasoning agent for creating HN-style digests."""

from typing import List, Dict, Any
from datetime import datetime
from ...models.article import ParsedArticle, DigestMetadata
from ...mcp_servers import get_tier2_server


class SynthesisAgent:
    """
    Tier 2 Synthesis Agent - Creates HN-style news digest from articles.

    Uses Sonnet for deep reasoning to synthesize articles into engaging,
    technical, and skeptical summaries that mimic Hacker News comment style.
    """

    def __init__(self):
        """Initialize Synthesis Agent with Tier 2 MCP server."""
        self.server = get_tier2_server()
        self.synthesis_count = 0

    async def create_digest(
        self,
        articles_by_topic: Dict[str, List[ParsedArticle]],
        user_preferences: Dict[str, Any],
        metadata: DigestMetadata
    ) -> str:
        """
        Create complete HN-style digest from articles organized by topic.

        Args:
            articles_by_topic: Dict mapping topic name to list of ParsedArticle
            user_preferences: User preferences configuration
            metadata: Digest metadata for inclusion

        Returns:
            Markdown-formatted digest string
        """
        self.synthesis_count += 1

        # Generate digest sections
        digest_parts = []

        # Header
        digest_parts.append(self._create_header(metadata))

        # Topic sections
        for topic_name, articles in articles_by_topic.items():
            if not articles:
                continue

            topic_section = await self._synthesize_topic_section(
                topic_name,
                articles,
                user_preferences
            )

            digest_parts.append(topic_section)

        # Footer with metadata
        digest_parts.append(self._create_footer(metadata))

        # Join all parts
        digest = "\n\n".join(digest_parts)

        return digest

    def _create_header(self, metadata: DigestMetadata) -> str:
        """
        Create digest header.

        Args:
            metadata: Digest metadata

        Returns:
            Markdown header string
        """
        date_str = metadata.generated_at.strftime("%B %d, %Y")

        header = f"""# Daily Tech Digest

**{date_str}**

*Your personalized HN-style news digest*

---
"""
        return header

    async def _synthesize_topic_section(
        self,
        topic_name: str,
        articles: List[ParsedArticle],
        user_preferences: Dict[str, Any]
    ) -> str:
        """
        Synthesize a single topic section.

        Args:
            topic_name: Name of the topic
            articles: List of parsed articles for this topic
            user_preferences: User preferences

        Returns:
            Markdown section for this topic
        """
        # Build articles summary for LLM
        articles_text = self._format_articles_for_synthesis(articles)

        # Create synthesis prompt
        prompt = f"""You are writing a Hacker News-style digest section about: {topic_name}

Articles to synthesize:
{articles_text}

Write an engaging section that:
1. Groups related articles together
2. Uses technical, skeptical HN-style commentary
3. Focuses on "why this matters" and implications
4. Highlights key technical details and trade-offs
5. Avoids hype - be measured and analytical
6. Each article gets 2-3 sentences maximum

Format:
## {topic_name}

[Your synthesis of the articles in HN comment style]

### Article Title 1
*Source: [source] | [reading time]*

[2-3 sentence HN-style summary focusing on implications and technical details]

[Source link]

---

Continue for each article. Be concise but insightful."""

        response = await self.server.complete(
            prompt=prompt,
            max_tokens=1500,
            temperature=0.7,  # Moderate creativity for engaging writing
            system_prompt="You are a veteran Hacker News commenter known for technical depth and skeptical analysis."
        )

        return response.content.strip()

    def _format_articles_for_synthesis(
        self,
        articles: List[ParsedArticle]
    ) -> str:
        """
        Format articles into text for LLM synthesis.

        Args:
            articles: List of ParsedArticle objects

        Returns:
            Formatted text string
        """
        formatted = []

        for i, article in enumerate(articles, 1):
            # Truncate content to avoid token limits
            content_preview = article.content[:800]

            formatted.append(f"""
Article {i}:
Title: {article.title}
Source: {article.source}
URL: {article.url}
Reading Time: {article.reading_time_minutes} min
Content Preview:
{content_preview}
""")

        return "\n---\n".join(formatted)

    def _create_footer(self, metadata: DigestMetadata) -> str:
        """
        Create digest footer with metadata.

        Args:
            metadata: Digest metadata

        Returns:
            Markdown footer string
        """
        footer = f"""---

## Digest Stats

- **Articles Found**: {metadata.total_articles_found}
- **Articles Parsed**: {metadata.total_articles_parsed}
- **Articles Included**: {metadata.total_articles_included}
- **Topics**: {', '.join(metadata.topics_covered)}
- **Processing Time**: {metadata.processing_time_seconds:.1f}s
- **Total Tokens Used**: {metadata.total_tokens_used:,}
- **Estimated Cost**: ${metadata.total_cost_usd:.4f}

---

*Generated by Intelligent News Aggregator v{metadata.preferences_version}*
*{metadata.generated_at.strftime("%Y-%m-%d %H:%M:%S")}*
"""
        return footer

    async def create_simple_summary(
        self,
        articles: List[ParsedArticle],
        max_articles: int = 5
    ) -> str:
        """
        Create a simple bullet-point summary (for testing).

        Args:
            articles: List of parsed articles
            max_articles: Maximum articles to include

        Returns:
            Simple markdown summary
        """
        summary_parts = ["# Quick Summary\n"]

        for i, article in enumerate(articles[:max_articles], 1):
            summary_parts.append(
                f"{i}. **{article.title}** ({article.source})\n"
                f"   {article.content_preview}\n"
                f"   [{article.url}]({article.url})\n"
            )

        return "\n".join(summary_parts)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get synthesis agent statistics.

        Returns:
            Dict with synthesis stats
        """
        return {
            "agent": "SynthesisAgent",
            "tier": "2",
            "synthesis_count": self.synthesis_count,
            "mcp_stats": self.server.get_stats()
        }
