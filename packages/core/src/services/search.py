"""Search service for article discovery.

Supports multiple search providers:
- Tavily: AI-focused search with quality results
- Brave: Privacy-focused web search
- Mock: For testing without API calls

Usage:
    from src.services import SearchService, SearchProvider

    # Create search service
    search = SearchService(api_key="tvly-...", provider=SearchProvider.TAVILY)

    # Search for articles
    results = await search.search("latest AI research", max_results=10)

    # Search with topic context
    results = await search.search_topic(
        topic_name="AI & Machine Learning",
        keywords=["LLM", "transformer", "neural network"],
        max_results=15,
    )
"""

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from urllib.parse import urlparse

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


class SearchProvider(Enum):
    """Available search providers."""

    TAVILY = "tavily"
    BRAVE = "brave"
    MOCK = "mock"


class SearchError(Exception):
    """Base exception for search errors."""

    def __init__(self, message: str, provider: str = "unknown", details: dict | None = None):
        super().__init__(message)
        self.provider = provider
        self.details = details or {}


class RateLimitError(SearchError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, provider: str, retry_after: float | None = None):
        super().__init__(message, provider)
        self.retry_after = retry_after


class QuotaExceededError(SearchError):
    """Raised when API quota is exceeded."""

    pass


@dataclass
class SearchConfig:
    """Configuration for search service."""

    provider: SearchProvider = SearchProvider.TAVILY
    api_key: str | None = None
    timeout: float = 30.0
    max_retries: int = 3
    include_domains: list[str] = field(default_factory=list)
    exclude_domains: list[str] = field(default_factory=list)
    search_depth: str = "advanced"  # "basic" or "advanced"
    include_answer: bool = False
    include_raw_content: bool = False
    include_images: bool = False

    @classmethod
    def from_env(cls) -> "SearchConfig":
        """Load config from environment variables."""
        provider_name = os.environ.get("SEARCH_PROVIDER", "tavily").lower()
        provider = SearchProvider(provider_name) if provider_name in ["tavily", "brave", "mock"] else SearchProvider.TAVILY

        return cls(
            provider=provider,
            api_key=os.environ.get("TAVILY_API_KEY") or os.environ.get("BRAVE_API_KEY"),
            timeout=float(os.environ.get("SEARCH_TIMEOUT", "30")),
        )


@dataclass
class SearchResult:
    """A single search result."""

    url: str
    title: str
    snippet: str
    source: str
    published_date: datetime | None = None
    relevance_score: float = 0.0
    rank: int = 0
    raw_content: str | None = None
    images: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def domain(self) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(self.url)
            return parsed.netloc.replace("www.", "")
        except Exception:
            return self.source

    @property
    def age_hours(self) -> float | None:
        """Age of article in hours."""
        if not self.published_date:
            return None
        delta = datetime.now() - self.published_date
        return delta.total_seconds() / 3600

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "source": self.source,
            "domain": self.domain,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "relevance_score": self.relevance_score,
            "rank": self.rank,
            "age_hours": self.age_hours,
        }


@dataclass
class SearchStats:
    """Statistics for search operations."""

    total_searches: int = 0
    total_results: int = 0
    total_time: float = 0.0
    errors: int = 0
    rate_limits: int = 0

    @property
    def average_time(self) -> float:
        """Average search time in seconds."""
        return self.total_time / self.total_searches if self.total_searches > 0 else 0.0

    @property
    def average_results(self) -> float:
        """Average results per search."""
        return self.total_results / self.total_searches if self.total_searches > 0 else 0.0


class SearchService:
    """
    Unified search service for article discovery.

    Supports Tavily and Brave Search APIs with automatic
    fallback and retry logic.
    """

    TAVILY_BASE_URL = "https://api.tavily.com"
    BRAVE_BASE_URL = "https://api.search.brave.com/res/v1"

    # High-quality news sources for filtering
    PREMIUM_SOURCES = [
        "arxiv.org",
        "nature.com",
        "science.org",
        "arstechnica.com",
        "wired.com",
        "techcrunch.com",
        "theverge.com",
        "news.ycombinator.com",
        "github.com",
        "openai.com",
        "anthropic.com",
        "deepmind.com",
        "mit.edu",
        "stanford.edu",
        "acm.org",
        "ieee.org",
    ]

    def __init__(
        self,
        config: SearchConfig | None = None,
        api_key: str | None = None,
        provider: SearchProvider = SearchProvider.TAVILY,
    ):
        """
        Initialize search service.

        Args:
            config: Search configuration (uses defaults if None)
            api_key: API key (overrides config if provided)
            provider: Search provider (overrides config if provided)
        """
        self.config = config or SearchConfig()
        if api_key:
            self.config.api_key = api_key
        if provider != SearchProvider.TAVILY:
            self.config.provider = provider

        self._stats = SearchStats()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.config.timeout)
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str | None = None,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        days_back: int | None = None,
    ) -> list[SearchResult]:
        """
        Search for articles matching query.

        Args:
            query: Search query string
            max_results: Maximum results to return
            search_depth: "basic" or "advanced" (default from config)
            include_domains: Limit to these domains
            exclude_domains: Exclude these domains
            days_back: Only return articles from last N days

        Returns:
            List of SearchResult objects

        Raises:
            SearchError: If search fails
        """
        if self.config.provider == SearchProvider.MOCK:
            return self._mock_search(query, max_results)

        if self.config.provider == SearchProvider.TAVILY:
            return await self._tavily_search(
                query=query,
                max_results=max_results,
                search_depth=search_depth or self.config.search_depth,
                include_domains=include_domains or self.config.include_domains,
                exclude_domains=exclude_domains or self.config.exclude_domains,
                days_back=days_back,
            )
        elif self.config.provider == SearchProvider.BRAVE:
            return await self._brave_search(
                query=query,
                max_results=max_results,
                days_back=days_back,
            )
        else:
            raise SearchError(f"Unknown provider: {self.config.provider}")

    async def _tavily_search(
        self,
        query: str,
        max_results: int,
        search_depth: str,
        include_domains: list[str],
        exclude_domains: list[str],
        days_back: int | None,
    ) -> list[SearchResult]:
        """Execute search using Tavily API."""
        if not self.config.api_key:
            raise SearchError("Tavily API key not configured", provider="tavily")

        start_time = time.time()
        client = await self._get_client()

        payload: dict[str, Any] = {
            "api_key": self.config.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": self.config.include_answer,
            "include_raw_content": self.config.include_raw_content,
            "include_images": self.config.include_images,
        }

        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains
        if days_back:
            payload["days"] = days_back

        try:
            response = await client.post(
                f"{self.TAVILY_BASE_URL}/search",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        except httpx.HTTPStatusError as e:
            self._handle_http_error(e, "tavily")

        except httpx.TimeoutException:
            self._stats.errors += 1
            raise SearchError(
                f"Search timed out after {self.config.timeout}s",
                provider="tavily",
            )

        except httpx.RequestError as e:
            self._stats.errors += 1
            raise SearchError(f"Search request failed: {str(e)}", provider="tavily")

        # Parse results
        results = []
        raw_results = data.get("results", [])

        for i, item in enumerate(raw_results):
            # Parse published date
            published_date = None
            if "published_date" in item:
                try:
                    published_date = datetime.fromisoformat(
                        item["published_date"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            result = SearchResult(
                url=item.get("url", ""),
                title=item.get("title", ""),
                snippet=item.get("content", item.get("snippet", "")),
                source=self._extract_source(item.get("url", "")),
                published_date=published_date,
                relevance_score=item.get("score", 0.0),
                rank=i + 1,
                raw_content=item.get("raw_content"),
                images=item.get("images", []),
                metadata={
                    "tavily_score": item.get("score"),
                },
            )
            results.append(result)

        # Update stats
        elapsed = time.time() - start_time
        self._stats.total_searches += 1
        self._stats.total_results += len(results)
        self._stats.total_time += elapsed

        return results

    async def _brave_search(
        self,
        query: str,
        max_results: int,
        days_back: int | None,
    ) -> list[SearchResult]:
        """Execute search using Brave Search API."""
        if not self.config.api_key:
            raise SearchError("Brave API key not configured", provider="brave")

        start_time = time.time()
        client = await self._get_client()

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.config.api_key,
        }

        params: dict[str, Any] = {
            "q": query,
            "count": max_results,
            "text_decorations": False,
        }

        if days_back:
            # Brave uses freshness parameter: pd (past day), pw (past week), pm (past month)
            if days_back <= 1:
                params["freshness"] = "pd"
            elif days_back <= 7:
                params["freshness"] = "pw"
            elif days_back <= 30:
                params["freshness"] = "pm"

        try:
            response = await client.get(
                f"{self.BRAVE_BASE_URL}/web/search",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        except httpx.HTTPStatusError as e:
            self._handle_http_error(e, "brave")

        except httpx.TimeoutException:
            self._stats.errors += 1
            raise SearchError(
                f"Search timed out after {self.config.timeout}s",
                provider="brave",
            )

        except httpx.RequestError as e:
            self._stats.errors += 1
            raise SearchError(f"Search request failed: {str(e)}", provider="brave")

        # Parse results
        results = []
        web_results = data.get("web", {}).get("results", [])

        for i, item in enumerate(web_results):
            # Parse published date
            published_date = None
            if "age" in item:
                # Brave returns relative age like "2 hours ago"
                published_date = self._parse_relative_date(item["age"])

            result = SearchResult(
                url=item.get("url", ""),
                title=item.get("title", ""),
                snippet=item.get("description", ""),
                source=self._extract_source(item.get("url", "")),
                published_date=published_date,
                relevance_score=1.0 - (i * 0.05),  # Estimate from rank
                rank=i + 1,
                metadata={
                    "brave_extra_snippets": item.get("extra_snippets", []),
                },
            )
            results.append(result)

        # Update stats
        elapsed = time.time() - start_time
        self._stats.total_searches += 1
        self._stats.total_results += len(results)
        self._stats.total_time += elapsed

        return results

    def _mock_search(self, query: str, max_results: int) -> list[SearchResult]:
        """Generate mock search results for testing."""
        results = []
        sources = ["arxiv.org", "techcrunch.com", "arstechnica.com", "wired.com", "nature.com"]

        for i in range(min(max_results, 10)):
            source = sources[i % len(sources)]
            results.append(
                SearchResult(
                    url=f"https://{source}/article/{i + 1}-{query[:20].replace(' ', '-')}",
                    title=f"Mock Article {i + 1}: {query[:50]}",
                    snippet=f"This is a mock search result about {query}. It contains relevant information for testing purposes.",
                    source=source,
                    published_date=datetime.now() - timedelta(hours=i * 2),
                    relevance_score=1.0 - (i * 0.08),
                    rank=i + 1,
                )
            )

        return results

    def _handle_http_error(self, error: httpx.HTTPStatusError, provider: str) -> None:
        """Handle HTTP errors from search APIs."""
        status_code = error.response.status_code

        try:
            error_data = error.response.json()
            error_message = error_data.get("error", str(error))
        except Exception:
            error_message = str(error)

        self._stats.errors += 1

        if status_code == 401:
            raise SearchError(f"Invalid API key: {error_message}", provider=provider)
        elif status_code == 429:
            self._stats.rate_limits += 1
            retry_after = error.response.headers.get("Retry-After")
            raise RateLimitError(
                f"Rate limit exceeded: {error_message}",
                provider=provider,
                retry_after=float(retry_after) if retry_after else None,
            )
        elif status_code == 402:
            raise QuotaExceededError(f"API quota exceeded: {error_message}", provider=provider)
        else:
            raise SearchError(
                f"Search failed ({status_code}): {error_message}",
                provider=provider,
            )

    def _extract_source(self, url: str) -> str:
        """Extract source name from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain
        except Exception:
            return "unknown"

    def _parse_relative_date(self, age_str: str) -> datetime | None:
        """Parse relative date string like '2 hours ago'."""
        try:
            age_str = age_str.lower()
            now = datetime.now()

            if "hour" in age_str:
                hours = int(age_str.split()[0])
                return now - timedelta(hours=hours)
            elif "day" in age_str:
                days = int(age_str.split()[0])
                return now - timedelta(days=days)
            elif "week" in age_str:
                weeks = int(age_str.split()[0])
                return now - timedelta(weeks=weeks)
            elif "month" in age_str:
                months = int(age_str.split()[0])
                return now - timedelta(days=months * 30)
            elif "minute" in age_str:
                minutes = int(age_str.split()[0])
                return now - timedelta(minutes=minutes)
            else:
                return None
        except Exception:
            return None

    async def search_topic(
        self,
        topic_name: str,
        keywords: list[str],
        max_results: int = 15,
        exclude_keywords: list[str] | None = None,
        days_back: int = 7,
        prefer_premium_sources: bool = True,
    ) -> list[SearchResult]:
        """
        Search for articles on a specific topic.

        Generates optimized search queries and combines results.

        Args:
            topic_name: Topic name for context
            keywords: Keywords to search for
            max_results: Maximum results to return
            exclude_keywords: Keywords to exclude
            days_back: Look back period in days
            prefer_premium_sources: Boost results from premium sources

        Returns:
            List of SearchResult objects, deduplicated and ranked
        """
        # Generate search queries
        queries = self._generate_topic_queries(topic_name, keywords, exclude_keywords)

        # Execute searches in parallel
        all_results: list[SearchResult] = []
        tasks = [
            self.search(
                query=query,
                max_results=max_results // len(queries) + 5,  # Get extra for dedup
                days_back=days_back,
            )
            for query in queries[:3]  # Limit to 3 queries to avoid rate limits
        ]

        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results_lists:
            if isinstance(result, list):
                all_results.extend(result)
            elif isinstance(result, Exception):
                # Log but continue with other results
                pass

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique_results: list[SearchResult] = []

        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)

        # Boost premium sources
        if prefer_premium_sources:
            for result in unique_results:
                if any(source in result.url for source in self.PREMIUM_SOURCES):
                    result.relevance_score = min(1.0, result.relevance_score + 0.15)

        # Sort by relevance
        unique_results.sort(key=lambda r: r.relevance_score, reverse=True)

        return unique_results[:max_results]

    def _generate_topic_queries(
        self,
        topic_name: str,
        keywords: list[str],
        exclude_keywords: list[str] | None = None,
    ) -> list[str]:
        """Generate search queries for a topic."""
        queries = []

        # Primary query with topic and top keywords
        primary = f"{topic_name} {' '.join(keywords[:3])}"
        if exclude_keywords:
            primary += " -" + " -".join(exclude_keywords[:2])
        queries.append(primary)

        # Alternative query focusing on recent news
        if keywords:
            queries.append(f"latest {keywords[0]} news {topic_name.split()[0]}")

        # Technical/research focused query
        if any(k in topic_name.lower() for k in ["ai", "ml", "machine learning", "science"]):
            queries.append(f"research paper {' '.join(keywords[:2])}")

        return queries

    def get_stats(self) -> dict[str, Any]:
        """Get search statistics."""
        return {
            "provider": self.config.provider.value,
            "total_searches": self._stats.total_searches,
            "total_results": self._stats.total_results,
            "average_results": self._stats.average_results,
            "total_time": self._stats.total_time,
            "average_time": self._stats.average_time,
            "errors": self._stats.errors,
            "rate_limits": self._stats.rate_limits,
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = SearchStats()
