"""Search Agent - Tier 1 execution agent for finding news articles."""

from typing import List, Dict, Any
import asyncio
from datetime import datetime
from ...models.article import ArticleURL
from ...mcp_servers import get_tier1_server


class SearchAgent:
    """
    Tier 1 Search Agent - Finds relevant articles on specified topics.

    Uses LLM (via MCP → Haiku) to generate search queries and process results.
    """

    def __init__(self):
        """Initialize Search Agent with Tier 1 MCP server."""
        self.server = get_tier1_server()
        self.search_count = 0

    async def search_topic(
        self,
        topic_name: str,
        keywords: List[str],
        exclude_keywords: List[str] = None,
        max_results: int = 10,
        sources: List[str] = None
    ) -> List[ArticleURL]:
        """
        Search for articles on a specific topic.

        Args:
            topic_name: Name of the topic (e.g., "AI & Machine Learning")
            keywords: List of keywords to search for
            exclude_keywords: Keywords to exclude from results
            max_results: Maximum number of URLs to return (default: 10)
            sources: Preferred sources to search within

        Returns:
            List of ArticleURL objects with search results
        """
        self.search_count += 1

        # Generate search query using LLM
        query = await self._generate_search_query(
            topic_name,
            keywords,
            exclude_keywords
        )

        # Execute mock search (Phase 1 - will integrate real search API in Phase 2)
        results = await self._execute_search(
            query,
            max_results,
            sources
        )

        # Process and rank results
        articles = await self._process_search_results(
            results,
            topic_name,
            keywords
        )

        return articles[:max_results]

    async def _generate_search_query(
        self,
        topic_name: str,
        keywords: List[str],
        exclude_keywords: List[str] = None
    ) -> str:
        """
        Generate optimal search query using LLM.

        Args:
            topic_name: Topic name
            keywords: Keywords to include
            exclude_keywords: Keywords to exclude

        Returns:
            Optimized search query string
        """
        exclude_keywords = exclude_keywords or []

        prompt = f"""Generate a search query for finding recent, high-quality articles about: {topic_name}

Include these concepts: {', '.join(keywords[:5])}
Exclude: {', '.join(exclude_keywords[:3]) if exclude_keywords else 'none'}

Requirements:
- Focus on recent news/research (last 30 days preferred)
- Prefer technical depth over clickbait
- Target sources like HN, ArsTechnica, ArXiv, Nature

Return ONLY the search query, no explanation."""

        response = await self.server.complete(
            prompt=prompt,
            max_tokens=100,
            temperature=0.3  # Low temperature for focused queries
        )

        # Extract and clean query
        query = response.content.strip().strip('"\'')

        return query

    async def _execute_search(
        self,
        query: str,
        max_results: int,
        sources: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute search query (Phase 1: mock implementation).

        Args:
            query: Search query
            max_results: Maximum results to return
            sources: Preferred sources

        Returns:
            List of search result dictionaries
        """
        # Phase 1: Return mock search results
        # In Phase 2+, integrate with Tavily or Brave Search API

        sources = sources or [
            "news.ycombinator.com",
            "arstechnica.com",
            "arxiv.org"
        ]

        mock_results = []

        # Generate mock results based on query
        for i in range(max_results):
            source = sources[i % len(sources)]

            mock_results.append({
                "url": f"https://{source}/article-{i + 1}-{query[:20].replace(' ', '-')}",
                "title": f"Mock Article {i + 1}: {query[:50]}",
                "snippet": f"This is a mock article about {query}. Contains relevant information and insights...",
                "source": source,
                "published_date": datetime.now().isoformat(),
                "rank": i + 1
            })

        return mock_results

    async def _process_search_results(
        self,
        results: List[Dict[str, Any]],
        topic_name: str,
        keywords: List[str]
    ) -> List[ArticleURL]:
        """
        Process search results into ArticleURL objects with relevance scores.

        Args:
            results: Raw search results
            topic_name: Topic name for context
            keywords: Keywords for relevance scoring

        Returns:
            List of ArticleURL objects with relevance scores
        """
        if not results:
            return []

        # Build scoring prompt for all results at once (more efficient)
        results_text = "\n\n".join([
            f"{i + 1}. Title: {r['title']}\n   Snippet: {r['snippet']}"
            for i, r in enumerate(results)
        ])

        prompt = f"""Rate the relevance of these search results for topic "{topic_name}".
Keywords: {', '.join(keywords[:5])}

Search Results:
{results_text}

For each result (1-{len(results)}), provide a relevance score from 0.0 to 1.0.
Format: "1: 0.85, 2: 0.72, 3: 0.91" etc.

Scores only, no explanation:"""

        response = await self.server.complete(
            prompt=prompt,
            max_tokens=100,
            temperature=0.2
        )

        # Parse scores from response
        scores = self._parse_relevance_scores(response.content, len(results))

        # Create ArticleURL objects
        articles = []
        for i, result in enumerate(results):
            # Parse published date
            published_date = None
            if "published_date" in result:
                try:
                    published_date = datetime.fromisoformat(
                        result["published_date"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            article = ArticleURL(
                url=result["url"],
                title=result["title"],
                source=result["source"],
                snippet=result.get("snippet", ""),
                published_date=published_date,
                initial_relevance_score=scores.get(i, 0.5),
                topic=topic_name,
                search_rank=result.get("rank", i + 1)
            )
            articles.append(article)

        # Sort by relevance score (descending)
        articles.sort(key=lambda a: a.initial_relevance_score, reverse=True)

        return articles

    def _parse_relevance_scores(
        self,
        scores_text: str,
        num_results: int
    ) -> Dict[int, float]:
        """
        Parse relevance scores from LLM response.

        Args:
            scores_text: LLM response with scores
            num_results: Expected number of results

        Returns:
            Dict mapping result index to score
        """
        scores = {}

        # Try to parse "1: 0.85, 2: 0.72" format
        import re
        matches = re.findall(r'(\d+):\s*([0-9.]+)', scores_text)

        for match in matches:
            idx = int(match[0]) - 1  # Convert to 0-indexed
            score = float(match[1])

            # Clamp score to [0, 1]
            score = max(0.0, min(1.0, score))
            scores[idx] = score

        # Fill in missing scores with default 0.5
        for i in range(num_results):
            if i not in scores:
                scores[i] = 0.5

        return scores

    def get_stats(self) -> Dict[str, Any]:
        """
        Get search agent statistics.

        Returns:
            Dict with search stats
        """
        return {
            "agent": "SearchAgent",
            "tier": "1",
            "search_count": self.search_count,
            "mcp_stats": self.server.get_stats()
        }
