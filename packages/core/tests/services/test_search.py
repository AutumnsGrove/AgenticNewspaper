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
    SearchError,
    RateLimitError,
)


# ============================================================================
# SearchResult Tests
# ============================================================================


class TestSearchResult:
    """Tests for the SearchResult dataclass."""

    def test_create_search_result(self):
        """Test creating a search result."""
        result = SearchResult(
            url="https://example.com/article",
            title="Test Article",
            snippet="This is a test article snippet.",
            source="example.com",
            relevance_score=0.85,
            published_date=datetime(2025, 12, 24),
        )
        assert result.title == "Test Article"
        assert result.url == "https://example.com/article"
        assert result.snippet == "This is a test article snippet."
        assert result.source == "example.com"
        assert result.relevance_score == 0.85
        assert result.published_date == datetime(2025, 12, 24)

    def test_search_result_with_defaults(self):
        """Test search result with default values."""
        result = SearchResult(
            url="https://example.com",
            title="Test",
            snippet="Snippet",
            source="example.com",
        )
        assert result.published_date is None
        assert result.relevance_score == 0.0
        assert result.rank == 0

    @pytest.mark.parametrize(
        "score",
        [0.0, 0.25, 0.5, 0.75, 1.0],
    )
    def test_score_range(self, score):
        """Test valid score ranges."""
        result = SearchResult(
            url="https://example.com",
            title="Test",
            snippet="Snippet",
            source="example.com",
            relevance_score=score,
        )
        assert 0 <= result.relevance_score <= 1

    def test_domain_property(self):
        """Test domain extraction property."""
        result = SearchResult(
            url="https://www.example.com/path/to/article",
            title="Test",
            snippet="Snippet",
            source="example.com",
        )
        assert result.domain == "example.com"

    def test_age_hours_property(self):
        """Test age calculation property."""
        result = SearchResult(
            url="https://example.com",
            title="Test",
            snippet="Snippet",
            source="example.com",
            published_date=datetime.now() - timedelta(hours=2),
        )
        assert result.age_hours is not None
        assert result.age_hours >= 2

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = SearchResult(
            url="https://example.com",
            title="Test",
            snippet="Snippet",
            source="example.com",
        )
        d = result.to_dict()
        assert "url" in d
        assert "title" in d
        assert "domain" in d
        assert "relevance_score" in d


# ============================================================================
# SearchConfig Tests
# ============================================================================


class TestSearchConfig:
    """Tests for SearchConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = SearchConfig()
        assert config.provider == SearchProvider.TAVILY
        assert config.timeout == 30.0
        assert config.max_retries == 3

    def test_custom_config(self):
        """Test custom configuration."""
        config = SearchConfig(
            provider=SearchProvider.BRAVE,
            api_key="test-key",
            timeout=60.0,
        )
        assert config.provider == SearchProvider.BRAVE
        assert config.api_key == "test-key"
        assert config.timeout == 60.0


# ============================================================================
# SearchStats Tests
# ============================================================================


class TestSearchStats:
    """Tests for SearchStats."""

    def test_default_stats(self):
        """Test default statistics."""
        stats = SearchStats()
        assert stats.total_searches == 0
        assert stats.total_results == 0
        assert stats.errors == 0

    def test_average_time(self):
        """Test average time calculation."""
        stats = SearchStats(total_searches=10, total_time=50.0)
        assert stats.average_time == 5.0

    def test_average_time_no_searches(self):
        """Test average time with no searches."""
        stats = SearchStats()
        assert stats.average_time == 0.0

    def test_average_results(self):
        """Test average results calculation."""
        stats = SearchStats(total_searches=10, total_results=150)
        assert stats.average_results == 15.0


# ============================================================================
# SearchService Mock Provider Tests
# ============================================================================


class TestSearchServiceMock:
    """Tests for SearchService with mock provider."""

    @pytest.fixture
    def service(self):
        """Create a search service with mock provider."""
        return SearchService(provider=SearchProvider.MOCK)

    @pytest.mark.asyncio
    async def test_mock_search_returns_results(self, service):
        """Test that mock search returns results."""
        results = await service.search("artificial intelligence")
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)

    @pytest.mark.asyncio
    async def test_mock_search_respects_max_results(self, service):
        """Test search with max results limit."""
        results = await service.search("test query", max_results=5)
        assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_mock_search_results_have_urls(self, service):
        """Test that results have valid URLs."""
        results = await service.search("test")
        for result in results:
            assert result.url.startswith("http")

    @pytest.mark.asyncio
    async def test_mock_search_results_have_titles(self, service):
        """Test that results have titles."""
        results = await service.search("test")
        for result in results:
            assert len(result.title) > 0

    @pytest.mark.asyncio
    async def test_mock_search_has_relevance_scores(self, service):
        """Test that mock results have relevance scores."""
        results = await service.search("test")
        for result in results:
            assert result.relevance_score >= 0
            assert result.relevance_score <= 1


# ============================================================================
# SearchService Tests
# ============================================================================


class TestSearchService:
    """Tests for the main SearchService class."""

    @pytest.fixture
    def service(self):
        """Create a search service with mock provider."""
        return SearchService(provider=SearchProvider.MOCK)

    @pytest.mark.asyncio
    async def test_search_single_query(self, service):
        """Test search with a single query."""
        results = await service.search("artificial intelligence")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_limits_results(self, service):
        """Test limiting the number of results."""
        results = await service.search("test", max_results=3)
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_search_topic_method(self, service):
        """Test search_topic method."""
        results = await service.search_topic(
            topic_name="AI & Machine Learning",
            keywords=["artificial intelligence", "LLM", "neural network"],
            max_results=10,
        )
        assert len(results) >= 0

    def test_generate_topic_queries(self, service):
        """Test query generation for topics."""
        queries = service._generate_topic_queries(
            topic_name="AI",
            keywords=["machine learning", "neural network"],
        )
        assert len(queries) > 0
        assert all(isinstance(q, str) for q in queries)

    def test_get_stats(self, service):
        """Test getting search statistics."""
        stats = service.get_stats()
        assert "provider" in stats
        assert "total_searches" in stats
        assert "errors" in stats

    def test_reset_stats(self, service):
        """Test resetting statistics."""
        service.reset_stats()
        stats = service.get_stats()
        assert stats["total_searches"] == 0


# ============================================================================
# Query Generation Tests
# ============================================================================


class TestQueryGeneration:
    """Tests for query generation functionality."""

    @pytest.fixture
    def service(self):
        """Create a search service."""
        return SearchService(provider=SearchProvider.MOCK)

    def test_query_includes_topic(self, service):
        """Test that generated queries include topic name."""
        queries = service._generate_topic_queries(
            topic_name="Science",
            keywords=["research", "study", "paper"],
        )
        # Primary query should include topic
        assert any("Science" in q for q in queries)

    def test_query_includes_keywords(self, service):
        """Test that generated queries include keywords."""
        queries = service._generate_topic_queries(
            topic_name="AI",
            keywords=["research", "study"],
        )
        all_text = " ".join(queries)
        assert "research" in all_text or "study" in all_text

    def test_query_with_exclude_keywords(self, service):
        """Test queries with excluded keywords."""
        queries = service._generate_topic_queries(
            topic_name="News",
            keywords=["breaking"],
            exclude_keywords=["spam", "ad"],
        )
        assert len(queries) > 0


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestSearchErrors:
    """Tests for search error handling."""

    def test_search_error_creation(self):
        """Test SearchError creation."""
        error = SearchError("Test error", provider="tavily")
        assert str(error) == "Test error"
        assert error.provider == "tavily"

    def test_rate_limit_error(self):
        """Test RateLimitError creation."""
        error = RateLimitError(
            "Rate limit exceeded",
            provider="tavily",
            retry_after=60.0,
        )
        assert error.retry_after == 60.0


# ============================================================================
# Integration Tests
# ============================================================================


class TestSearchServiceIntegration:
    """Integration tests for search service."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test full search workflow."""
        service = SearchService(provider=SearchProvider.MOCK)

        # Execute search
        results = await service.search_topic(
            topic_name="AI",
            keywords=["artificial intelligence", "machine learning"],
            max_results=10,
        )
        assert len(results) >= 0

        # Results should be sorted by relevance
        if len(results) >= 2:
            assert results[0].relevance_score >= results[-1].relevance_score

    @pytest.mark.asyncio
    async def test_concurrent_searches(self):
        """Test concurrent search execution."""
        import asyncio

        service = SearchService(provider=SearchProvider.MOCK)
        queries = ["query1", "query2", "query3", "query4", "query5"]

        # Execute all searches concurrently
        tasks = [service.search(q) for q in queries]
        all_results = await asyncio.gather(*tasks)

        assert len(all_results) == 5
        for results in all_results:
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager usage."""
        async with SearchService(provider=SearchProvider.MOCK) as service:
            results = await service.search("test")
            assert len(results) >= 0


# ============================================================================
# Provider Tests
# ============================================================================


class TestSearchProvider:
    """Tests for SearchProvider enum."""

    def test_tavily_provider(self):
        """Test Tavily provider value."""
        assert SearchProvider.TAVILY.value == "tavily"

    def test_brave_provider(self):
        """Test Brave provider value."""
        assert SearchProvider.BRAVE.value == "brave"

    def test_mock_provider(self):
        """Test Mock provider value."""
        assert SearchProvider.MOCK.value == "mock"
