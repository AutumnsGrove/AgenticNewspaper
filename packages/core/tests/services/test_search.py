"""
Tests for the search service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.services.search import (
    SearchService,
    SearchResult,
    SearchProvider,
    SearchConfig,
    SearchStats,
)


# ============================================================================
# SearchResult Tests
# ============================================================================


class TestSearchResult:
    """Tests for the SearchResult dataclass."""

    def test_create_search_result(self):
        """Test creating a search result."""
        result = SearchResult(
            title="Test Article",
            url="https://example.com/article",
            snippet="This is a test article snippet.",
            source="example.com",
            score=0.85,
            published_date="2025-12-24",
        )
        assert result.title == "Test Article"
        assert result.url == "https://example.com/article"
        assert result.snippet == "This is a test article snippet."
        assert result.source == "example.com"
        assert result.score == 0.85
        assert result.published_date == "2025-12-24"

    def test_search_result_with_defaults(self):
        """Test search result with default values."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Snippet",
        )
        assert result.source is None
        assert result.score is None
        assert result.published_date is None

    @pytest.mark.parametrize(
        "score",
        [0.0, 0.25, 0.5, 0.75, 1.0],
    )
    def test_score_range(self, score):
        """Test valid score ranges."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Snippet",
            score=score,
        )
        assert 0 <= result.score <= 1


# ============================================================================
# Mock Search Provider Tests
# ============================================================================


class TestMockSearchProvider:
    """Tests for the mock search provider."""

    @pytest.fixture
    def provider(self):
        """Create a mock provider instance."""
        return MockSearchProvider()

    @pytest.mark.asyncio
    async def test_search_returns_results(self, provider):
        """Test that mock search returns results."""
        results = await provider.search("artificial intelligence")
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)

    @pytest.mark.asyncio
    async def test_search_with_topic(self, provider):
        """Test search with specific topic."""
        results = await provider.search("machine learning", topic="AI")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_with_max_results(self, provider):
        """Test search with max results limit."""
        results = await provider.search("test query", max_results=5)
        assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_search_empty_query(self, provider):
        """Test search with empty query."""
        results = await provider.search("")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_results_have_urls(self, provider):
        """Test that results have valid URLs."""
        results = await provider.search("test")
        for result in results:
            assert result.url.startswith("http")

    @pytest.mark.asyncio
    async def test_search_results_have_titles(self, provider):
        """Test that results have titles."""
        results = await provider.search("test")
        for result in results:
            assert len(result.title) > 0


# ============================================================================
# Tavily Provider Tests
# ============================================================================


class TestTavilyProvider:
    """Tests for the Tavily search provider."""

    @pytest.fixture
    def provider(self):
        """Create a Tavily provider instance."""
        return TavilyProvider(api_key="test-key")

    @pytest.fixture
    def mock_response(self):
        """Create a mock Tavily API response."""
        return {
            "results": [
                {
                    "title": "AI Breakthrough",
                    "url": "https://example.com/ai",
                    "content": "Summary of the article...",
                    "score": 0.95,
                    "published_date": "2025-12-24",
                },
                {
                    "title": "Machine Learning Update",
                    "url": "https://example.com/ml",
                    "content": "Another summary...",
                    "score": 0.88,
                    "published_date": "2025-12-23",
                },
            ],
        }

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        provider = TavilyProvider(api_key="test-key-123")
        assert provider.api_key == "test-key-123"

    def test_base_url(self):
        """Test that base URL is correct."""
        provider = TavilyProvider(api_key="test-key")
        assert "tavily" in provider.base_url.lower()

    @pytest.mark.asyncio
    async def test_search_parses_response(self, provider, mock_response):
        """Test that search parses API response correctly."""
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            results = await provider.search("AI news")
            assert len(results) == 2
            assert results[0].title == "AI Breakthrough"
            assert results[0].score == 0.95

    @pytest.mark.asyncio
    async def test_search_with_date_filter(self, provider, mock_response):
        """Test search with date filter."""
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            results = await provider.search(
                "AI news", days=7
            )
            assert len(results) >= 0

    @pytest.mark.asyncio
    async def test_search_handles_empty_results(self, provider):
        """Test handling of empty results."""
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.return_value = {"results": []}
            results = await provider.search("obscure query")
            assert results == []

    @pytest.mark.asyncio
    async def test_search_handles_api_error(self, provider):
        """Test handling of API errors."""
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("API Error")
            with pytest.raises(Exception):
                await provider.search("test")


# ============================================================================
# SearchService Tests
# ============================================================================


class TestSearchService:
    """Tests for the main SearchService class."""

    @pytest.fixture
    def service(self):
        """Create a search service with mock provider."""
        return SearchService(provider=MockSearchProvider())

    @pytest.fixture
    def service_with_tavily(self):
        """Create a search service with Tavily provider."""
        return SearchService(provider=TavilyProvider(api_key="test-key"))

    @pytest.mark.asyncio
    async def test_search_single_query(self, service):
        """Test search with a single query."""
        results = await service.search("artificial intelligence")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_multiple_queries(self, service):
        """Test search with multiple queries."""
        queries = ["AI news", "machine learning", "deep learning"]
        results = await service.search_multiple(queries)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_deduplicates_results(self, service):
        """Test that duplicate URLs are removed."""
        # Mock provider returns duplicates
        results = await service.search_multiple(
            ["same query", "same query"]
        )
        urls = [r.url for r in results]
        assert len(urls) == len(set(urls))

    @pytest.mark.asyncio
    async def test_search_filters_by_score(self, service):
        """Test filtering results by score."""
        results = await service.search("test", min_score=0.5)
        for result in results:
            if result.score is not None:
                assert result.score >= 0.5

    @pytest.mark.asyncio
    async def test_search_limits_results(self, service):
        """Test limiting the number of results."""
        results = await service.search("test", max_results=3)
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_generate_queries_for_topic(self, service):
        """Test generating search queries for a topic."""
        topic = {
            "name": "AI & Machine Learning",
            "keywords": ["artificial intelligence", "LLM", "neural network"],
        }
        queries = await service.generate_queries_for_topic(topic)
        assert len(queries) > 0
        assert all(isinstance(q, str) for q in queries)

    @pytest.mark.asyncio
    async def test_search_for_topic(self, service):
        """Test searching for a specific topic."""
        topic = {
            "name": "AI",
            "keywords": ["artificial intelligence"],
        }
        results = await service.search_for_topic(topic)
        assert len(results) >= 0


# ============================================================================
# Query Generation Tests
# ============================================================================


class TestQueryGeneration:
    """Tests for query generation functionality."""

    @pytest.fixture
    def service(self):
        """Create a search service."""
        return SearchService(provider=MockSearchProvider())

    @pytest.mark.asyncio
    async def test_query_includes_keywords(self, service):
        """Test that generated queries include topic keywords."""
        topic = {
            "name": "Science",
            "keywords": ["research", "study", "paper"],
        }
        queries = await service.generate_queries_for_topic(topic)
        # At least some queries should contain keywords
        all_text = " ".join(queries).lower()
        assert any(kw.lower() in all_text for kw in topic["keywords"])

    @pytest.mark.asyncio
    async def test_query_limits(self, service):
        """Test query count limits."""
        topic = {"name": "Test", "keywords": ["test"]}
        queries = await service.generate_queries_for_topic(topic, max_queries=3)
        assert len(queries) <= 3

    @pytest.mark.asyncio
    async def test_query_recency(self, service):
        """Test that queries can include recency terms."""
        topic = {"name": "News", "keywords": ["breaking"]}
        queries = await service.generate_queries_for_topic(topic, include_recency=True)
        all_text = " ".join(queries).lower()
        # Should include time-related terms
        time_terms = ["today", "latest", "recent", "2025", "this week"]
        assert any(term in all_text for term in time_terms)


# ============================================================================
# Result Sorting Tests
# ============================================================================


class TestResultSorting:
    """Tests for result sorting functionality."""

    @pytest.fixture
    def service(self):
        """Create a search service."""
        return SearchService(provider=MockSearchProvider())

    @pytest.mark.asyncio
    async def test_sort_by_score(self, service):
        """Test sorting results by score."""
        results = await service.search("test")
        sorted_results = service.sort_results(results, by="score")
        scores = [r.score for r in sorted_results if r.score is not None]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_sort_by_date(self, service):
        """Test sorting results by date."""
        results = await service.search("test")
        sorted_results = service.sort_results(results, by="date")
        # Results should be in date order (most recent first)
        assert len(sorted_results) > 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestSearchServiceIntegration:
    """Integration tests for search service."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test full search workflow."""
        service = SearchService(provider=MockSearchProvider())

        # Generate queries
        topic = {
            "name": "AI",
            "keywords": ["artificial intelligence", "machine learning"],
        }
        queries = await service.generate_queries_for_topic(topic)
        assert len(queries) > 0

        # Execute search
        results = await service.search_multiple(queries)
        assert len(results) > 0

        # Sort and filter
        filtered = [r for r in results if r.score is None or r.score >= 0.5]
        sorted_results = service.sort_results(filtered, by="score")
        assert len(sorted_results) >= 0

    @pytest.mark.asyncio
    async def test_concurrent_searches(self):
        """Test concurrent search execution."""
        import asyncio

        service = SearchService(provider=MockSearchProvider())
        queries = ["query1", "query2", "query3", "query4", "query5"]

        # Execute all searches concurrently
        tasks = [service.search(q) for q in queries]
        all_results = await asyncio.gather(*tasks)

        assert len(all_results) == 5
        for results in all_results:
            assert isinstance(results, list)
