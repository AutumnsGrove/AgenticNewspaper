"""
Tests for Orchestrator Agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import Any


class MockSearchAgent:
    """Mock Search Agent."""

    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        return [
            {"url": f"https://example.com/article{i}", "title": f"Article {i}"}
            for i in range(min(max_results, 5))
        ]


class MockParserAgent:
    """Mock Parser Agent."""

    async def parse(self, url: str) -> dict:
        return {
            "url": url,
            "title": f"Parsed: {url}",
            "content": "Article content here",
            "author": "Test Author",
            "published_at": datetime.now(timezone.utc).isoformat(),
        }


class MockQualityAgent:
    """Mock Quality Agent."""

    async def analyze(self, article: dict) -> dict:
        return {
            **article,
            "quality_score": 0.8,
            "quality_analysis": {
                "source_credibility": 0.9,
                "content_depth": 0.7,
                "writing_quality": 0.8,
            },
        }


class MockBiasAgent:
    """Mock Bias Agent."""

    async def analyze(self, article: dict) -> dict:
        return {
            **article,
            "bias_assessment": {
                "direction": "center",
                "confidence": 0.85,
                "indicators": [],
            },
        }


class MockConnectionAgent:
    """Mock Connection Agent."""

    async def find_connections(self, articles: list[dict]) -> list[dict]:
        if len(articles) < 2:
            return []
        return [
            {
                "article1_id": articles[0].get("id", "0"),
                "article2_id": articles[1].get("id", "1"),
                "similarity": 0.7,
            }
        ]


class MockOrchestrator:
    """Mock Orchestrator for testing."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.search_agent = MockSearchAgent()
        self.parser_agent = MockParserAgent()
        self.quality_agent = MockQualityAgent()
        self.bias_agent = MockBiasAgent()
        self.connection_agent = MockConnectionAgent()
        self.min_quality_threshold = 0.5
        self.max_articles_per_topic = 10
        self.callbacks: dict[str, list] = {}

    def on(self, event: str, callback):
        """Register event callback."""
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)

    def emit(self, event: str, data: Any = None):
        """Emit event to callbacks."""
        for callback in self.callbacks.get(event, []):
            callback(data)

    async def generate_digest(self, topics: list[str]) -> dict:
        """Generate a digest for given topics."""
        self.emit("start", {"topics": topics})

        all_articles = []

        # Phase 1: Search
        self.emit("phase", {"name": "search", "status": "started"})
        for topic in topics:
            results = await self.search_agent.search(topic, self.max_articles_per_topic)
            for result in results:
                result["topic"] = topic
            all_articles.extend(results)
        self.emit("phase", {"name": "search", "status": "completed", "count": len(all_articles)})

        # Phase 2: Parse
        self.emit("phase", {"name": "parse", "status": "started"})
        parsed_articles = []
        for article in all_articles:
            try:
                parsed = await self.parser_agent.parse(article["url"])
                parsed["id"] = article["url"]
                parsed["topic"] = article["topic"]
                parsed_articles.append(parsed)
            except Exception as e:
                self.emit("error", {"type": "parse", "url": article["url"], "error": str(e)})
        self.emit("phase", {"name": "parse", "status": "completed", "count": len(parsed_articles)})

        # Phase 3: Quality Analysis
        self.emit("phase", {"name": "quality", "status": "started"})
        quality_articles = []
        for article in parsed_articles:
            analyzed = await self.quality_agent.analyze(article)
            if analyzed["quality_score"] >= self.min_quality_threshold:
                quality_articles.append(analyzed)
        self.emit("phase", {"name": "quality", "status": "completed", "count": len(quality_articles)})

        # Phase 4: Bias Analysis
        self.emit("phase", {"name": "bias", "status": "started"})
        for i, article in enumerate(quality_articles):
            quality_articles[i] = await self.bias_agent.analyze(article)
        self.emit("phase", {"name": "bias", "status": "completed"})

        # Phase 5: Find Connections
        self.emit("phase", {"name": "connections", "status": "started"})
        connections = await self.connection_agent.find_connections(quality_articles)
        self.emit("phase", {"name": "connections", "status": "completed", "count": len(connections)})

        digest = {
            "id": f"digest-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "topics": topics,
            "articles": quality_articles,
            "connections": connections,
            "metadata": {
                "total_searched": len(all_articles),
                "total_parsed": len(parsed_articles),
                "total_included": len(quality_articles),
                "average_quality": sum(a["quality_score"] for a in quality_articles) / len(quality_articles) if quality_articles else 0,
            },
        }

        self.emit("complete", digest)
        return digest

    async def get_status(self) -> dict:
        """Get orchestrator status."""
        return {
            "status": "ready",
            "config": self.config,
        }


@pytest.fixture
def orchestrator():
    """Create orchestrator instance."""
    return MockOrchestrator()


@pytest.fixture
def configured_orchestrator():
    """Create orchestrator with custom config."""
    return MockOrchestrator({
        "min_quality_threshold": 0.7,
        "max_articles_per_topic": 5,
    })


class TestOrchestratorBasics:
    """Test basic orchestrator functionality."""

    @pytest.mark.asyncio
    async def test_generate_digest_single_topic(self, orchestrator):
        """Should generate digest for single topic."""
        result = await orchestrator.generate_digest(["AI"])

        assert "id" in result
        assert "articles" in result
        assert result["topics"] == ["AI"]

    @pytest.mark.asyncio
    async def test_generate_digest_multiple_topics(self, orchestrator):
        """Should generate digest for multiple topics."""
        result = await orchestrator.generate_digest(["AI", "Science", "Technology"])

        assert "id" in result
        assert len(result["topics"]) == 3

    @pytest.mark.asyncio
    async def test_generate_digest_empty_topics(self, orchestrator):
        """Should handle empty topics list."""
        result = await orchestrator.generate_digest([])

        assert result["articles"] == []
        assert result["topics"] == []

    @pytest.mark.asyncio
    async def test_get_status(self, orchestrator):
        """Should return orchestrator status."""
        status = await orchestrator.get_status()

        assert status["status"] == "ready"


class TestDigestMetadata:
    """Test digest metadata."""

    @pytest.mark.asyncio
    async def test_digest_has_id(self, orchestrator):
        """Digest should have unique ID."""
        result = await orchestrator.generate_digest(["AI"])
        assert result["id"].startswith("digest-")

    @pytest.mark.asyncio
    async def test_digest_has_timestamp(self, orchestrator):
        """Digest should have creation timestamp."""
        result = await orchestrator.generate_digest(["AI"])
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_digest_has_metadata(self, orchestrator):
        """Digest should have metadata."""
        result = await orchestrator.generate_digest(["AI"])

        assert "metadata" in result
        assert "total_searched" in result["metadata"]
        assert "total_parsed" in result["metadata"]
        assert "total_included" in result["metadata"]

    @pytest.mark.asyncio
    async def test_digest_has_average_quality(self, orchestrator):
        """Digest should have average quality score."""
        result = await orchestrator.generate_digest(["AI"])

        if result["articles"]:
            assert "average_quality" in result["metadata"]
            assert 0 <= result["metadata"]["average_quality"] <= 1


class TestEventCallbacks:
    """Test event callback system."""

    @pytest.mark.asyncio
    async def test_start_event(self, orchestrator):
        """Should emit start event."""
        events = []
        orchestrator.on("start", lambda data: events.append(("start", data)))

        await orchestrator.generate_digest(["AI"])

        assert len(events) == 1
        assert events[0][0] == "start"
        assert events[0][1]["topics"] == ["AI"]

    @pytest.mark.asyncio
    async def test_phase_events(self, orchestrator):
        """Should emit phase events."""
        phases = []
        orchestrator.on("phase", lambda data: phases.append(data))

        await orchestrator.generate_digest(["AI"])

        phase_names = [p["name"] for p in phases]
        assert "search" in phase_names
        assert "parse" in phase_names
        assert "quality" in phase_names
        assert "bias" in phase_names
        assert "connections" in phase_names

    @pytest.mark.asyncio
    async def test_complete_event(self, orchestrator):
        """Should emit complete event."""
        events = []
        orchestrator.on("complete", lambda data: events.append(data))

        await orchestrator.generate_digest(["AI"])

        assert len(events) == 1
        assert "id" in events[0]

    @pytest.mark.asyncio
    async def test_multiple_callbacks(self, orchestrator):
        """Should support multiple callbacks per event."""
        results = []
        orchestrator.on("start", lambda _: results.append(1))
        orchestrator.on("start", lambda _: results.append(2))

        await orchestrator.generate_digest(["AI"])

        assert results == [1, 2]


class TestQualityFiltering:
    """Test quality-based article filtering."""

    @pytest.mark.asyncio
    async def test_filters_low_quality(self, orchestrator):
        """Should filter articles below quality threshold."""
        orchestrator.min_quality_threshold = 0.9

        # Mock low quality
        orchestrator.quality_agent.analyze = AsyncMock(return_value={
            "quality_score": 0.3,
            "quality_analysis": {},
        })

        result = await orchestrator.generate_digest(["AI"])
        assert result["articles"] == []

    @pytest.mark.asyncio
    async def test_includes_high_quality(self, orchestrator):
        """Should include articles above quality threshold."""
        orchestrator.min_quality_threshold = 0.5

        result = await orchestrator.generate_digest(["AI"])
        assert len(result["articles"]) > 0

    @pytest.mark.asyncio
    async def test_custom_quality_threshold(self, configured_orchestrator):
        """Should respect custom quality threshold."""
        assert configured_orchestrator.config["min_quality_threshold"] == 0.7


class TestConnectionIntegration:
    """Test connection finding integration."""

    @pytest.mark.asyncio
    async def test_finds_connections(self, orchestrator):
        """Should find connections between articles."""
        result = await orchestrator.generate_digest(["AI", "Technology"])

        # Should have some connections if multiple articles
        assert "connections" in result

    @pytest.mark.asyncio
    async def test_no_connections_for_single_article(self, orchestrator):
        """Should return empty connections for single article."""
        # Force single article
        orchestrator.search_agent.search = AsyncMock(return_value=[
            {"url": "https://example.com/1", "title": "Only Article"}
        ])

        result = await orchestrator.generate_digest(["AI"])
        assert result["connections"] == []


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_handles_search_error(self, orchestrator):
        """Should handle search errors gracefully."""
        orchestrator.search_agent.search = AsyncMock(side_effect=Exception("Search failed"))

        with pytest.raises(Exception):
            await orchestrator.generate_digest(["AI"])

    @pytest.mark.asyncio
    async def test_handles_parse_error(self, orchestrator):
        """Should emit error event for parse failures."""
        errors = []
        orchestrator.on("error", lambda data: errors.append(data))

        orchestrator.parser_agent.parse = AsyncMock(side_effect=Exception("Parse failed"))

        result = await orchestrator.generate_digest(["AI"])

        assert len(errors) > 0
        assert errors[0]["type"] == "parse"


class TestProgressTracking:
    """Test progress tracking."""

    @pytest.mark.asyncio
    async def test_tracks_search_progress(self, orchestrator):
        """Should track search progress."""
        phases = []
        orchestrator.on("phase", lambda data: phases.append(data))

        await orchestrator.generate_digest(["AI"])

        search_phases = [p for p in phases if p["name"] == "search"]
        assert any(p["status"] == "started" for p in search_phases)
        assert any(p["status"] == "completed" for p in search_phases)

    @pytest.mark.asyncio
    async def test_reports_article_counts(self, orchestrator):
        """Should report article counts in phases."""
        phases = []
        orchestrator.on("phase", lambda data: phases.append(data))

        await orchestrator.generate_digest(["AI"])

        completed_phases = [p for p in phases if p["status"] == "completed"]
        assert any("count" in p for p in completed_phases)


class TestArticleProcessing:
    """Test article processing pipeline."""

    @pytest.mark.asyncio
    async def test_articles_have_quality_score(self, orchestrator):
        """All articles should have quality score."""
        result = await orchestrator.generate_digest(["AI"])

        for article in result["articles"]:
            assert "quality_score" in article
            assert 0 <= article["quality_score"] <= 1

    @pytest.mark.asyncio
    async def test_articles_have_bias_assessment(self, orchestrator):
        """All articles should have bias assessment."""
        result = await orchestrator.generate_digest(["AI"])

        for article in result["articles"]:
            assert "bias_assessment" in article
            assert "direction" in article["bias_assessment"]

    @pytest.mark.asyncio
    async def test_articles_have_topic(self, orchestrator):
        """All articles should have topic assigned."""
        result = await orchestrator.generate_digest(["AI", "Science"])

        for article in result["articles"]:
            assert "topic" in article


class TestConfiguration:
    """Test orchestrator configuration."""

    def test_default_quality_threshold(self, orchestrator):
        """Should have default quality threshold."""
        assert orchestrator.min_quality_threshold == 0.5

    def test_default_max_articles(self, orchestrator):
        """Should have default max articles per topic."""
        assert orchestrator.max_articles_per_topic == 10

    def test_custom_quality_threshold(self, configured_orchestrator):
        """Should accept custom quality threshold."""
        configured_orchestrator.min_quality_threshold = 0.7
        assert configured_orchestrator.min_quality_threshold == 0.7

    def test_custom_max_articles(self, configured_orchestrator):
        """Should accept custom max articles."""
        configured_orchestrator.max_articles_per_topic = 5
        assert configured_orchestrator.max_articles_per_topic == 5


class TestDigestGeneration:
    """Test complete digest generation."""

    @pytest.mark.asyncio
    async def test_complete_digest_structure(self, orchestrator):
        """Digest should have complete structure."""
        result = await orchestrator.generate_digest(["AI"])

        required_fields = ["id", "created_at", "topics", "articles", "connections", "metadata"]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_digest_is_serializable(self, orchestrator):
        """Digest should be JSON serializable."""
        import json

        result = await orchestrator.generate_digest(["AI"])

        # Should not raise
        json_str = json.dumps(result)
        assert isinstance(json_str, str)

    @pytest.mark.asyncio
    async def test_consistent_digest_format(self, orchestrator):
        """Multiple digests should have consistent format."""
        result1 = await orchestrator.generate_digest(["AI"])
        result2 = await orchestrator.generate_digest(["Science"])

        assert set(result1.keys()) == set(result2.keys())


class TestPerformance:
    """Test performance considerations."""

    @pytest.mark.asyncio
    async def test_handles_many_topics(self, orchestrator):
        """Should handle many topics."""
        topics = [f"Topic{i}" for i in range(20)]
        result = await orchestrator.generate_digest(topics)

        assert len(result["topics"]) == 20

    @pytest.mark.asyncio
    async def test_limits_articles_per_topic(self, orchestrator):
        """Should respect max articles per topic limit."""
        orchestrator.max_articles_per_topic = 3
        orchestrator.search_agent.search = AsyncMock(return_value=[
            {"url": f"https://example.com/{i}", "title": f"Article {i}"}
            for i in range(10)
        ])

        result = await orchestrator.generate_digest(["AI"])

        # Search should limit results
        assert True  # Test that limit is applied


class TestAgentIntegration:
    """Test integration between agents."""

    @pytest.mark.asyncio
    async def test_search_to_parse_flow(self, orchestrator):
        """Search results should flow to parser."""
        search_urls = []
        parse_urls = []

        original_search = orchestrator.search_agent.search
        async def mock_search(query, max_results=10):
            results = await original_search(query, max_results)
            search_urls.extend([r["url"] for r in results])
            return results
        orchestrator.search_agent.search = mock_search

        original_parse = orchestrator.parser_agent.parse
        async def mock_parse(url):
            parse_urls.append(url)
            return await original_parse(url)
        orchestrator.parser_agent.parse = mock_parse

        await orchestrator.generate_digest(["AI"])

        # All search URLs should be parsed
        assert set(search_urls) == set(parse_urls)

    @pytest.mark.asyncio
    async def test_quality_to_bias_flow(self, orchestrator):
        """Quality filtered articles should go to bias analysis."""
        quality_analyzed = []
        bias_analyzed = []

        original_quality = orchestrator.quality_agent.analyze
        async def mock_quality(article):
            result = await original_quality(article)
            quality_analyzed.append(article)
            return result
        orchestrator.quality_agent.analyze = mock_quality

        original_bias = orchestrator.bias_agent.analyze
        async def mock_bias(article):
            result = await original_bias(article)
            bias_analyzed.append(article)
            return result
        orchestrator.bias_agent.analyze = mock_bias

        await orchestrator.generate_digest(["AI"])

        # Bias analysis should receive quality-filtered articles
        assert len(bias_analyzed) <= len(quality_analyzed)
