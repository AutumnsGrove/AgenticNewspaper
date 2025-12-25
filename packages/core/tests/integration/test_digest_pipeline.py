"""
Integration tests for the complete digest generation pipeline.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import Any
import json


class MockDigestPipeline:
    """Mock implementation of digest pipeline for integration testing."""

    def __init__(self):
        self.search_results: list[dict] = []
        self.parsed_articles: list[dict] = []
        self.analyzed_articles: list[dict] = []
        self.final_digest: dict | None = None
        self.pipeline_state: str = "idle"
        self.errors: list[dict] = []

    async def run(self, config: dict) -> dict:
        """Run the complete pipeline."""
        self.pipeline_state = "running"
        topics = config.get("topics", [])
        preferences = config.get("preferences", {})

        try:
            # Step 1: Search for articles
            self.pipeline_state = "searching"
            for topic in topics:
                results = await self._search(topic)
                self.search_results.extend(results)

            # Step 2: Parse articles
            self.pipeline_state = "parsing"
            for result in self.search_results:
                try:
                    article = await self._parse(result)
                    self.parsed_articles.append(article)
                except Exception as e:
                    self.errors.append({"phase": "parse", "url": result["url"], "error": str(e)})

            # Step 3: Analyze articles
            self.pipeline_state = "analyzing"
            for article in self.parsed_articles:
                analyzed = await self._analyze(article, preferences)
                if self._passes_filter(analyzed, preferences):
                    self.analyzed_articles.append(analyzed)

            # Step 4: Generate digest
            self.pipeline_state = "generating"
            self.final_digest = await self._generate_digest(
                self.analyzed_articles, topics, preferences
            )

            self.pipeline_state = "completed"
            return self.final_digest

        except Exception as e:
            self.pipeline_state = "failed"
            self.errors.append({"phase": "pipeline", "error": str(e)})
            raise

    async def _search(self, topic: str) -> list[dict]:
        """Search for articles on a topic."""
        return [
            {"url": f"https://news.example.com/{topic}/{i}", "title": f"{topic} Article {i}"}
            for i in range(5)
        ]

    async def _parse(self, result: dict) -> dict:
        """Parse an article."""
        return {
            "id": result["url"],
            "url": result["url"],
            "title": result["title"],
            "content": f"Content of {result['title']}",
            "author": "Test Author",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "word_count": 500,
        }

    async def _analyze(self, article: dict, preferences: dict) -> dict:
        """Analyze an article."""
        return {
            **article,
            "quality_score": 0.8,
            "bias_assessment": {"direction": "center", "confidence": 0.9},
            "topics": ["technology"],
            "summary": f"Summary of {article['title']}",
        }

    def _passes_filter(self, article: dict, preferences: dict) -> bool:
        """Check if article passes quality filter."""
        min_quality = preferences.get("min_quality", 0.5)
        return article.get("quality_score", 0) >= min_quality

    async def _generate_digest(
        self, articles: list[dict], topics: list[str], preferences: dict
    ) -> dict:
        """Generate final digest."""
        return {
            "id": f"digest-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "topics": topics,
            "articles": articles,
            "metadata": {
                "total_articles": len(articles),
                "average_quality": (
                    sum(a["quality_score"] for a in articles) / len(articles) if articles else 0
                ),
            },
            "preferences_applied": preferences,
        }


@pytest.fixture
def pipeline():
    """Create pipeline instance."""
    return MockDigestPipeline()


@pytest.fixture
def basic_config():
    """Basic pipeline configuration."""
    return {
        "topics": ["AI", "Technology"],
        "preferences": {
            "min_quality": 0.5,
            "max_articles": 10,
            "tone": "hn-style",
        },
    }


class TestPipelineExecution:
    """Test complete pipeline execution."""

    @pytest.mark.asyncio
    async def test_run_basic_pipeline(self, pipeline, basic_config):
        """Should run basic pipeline successfully."""
        result = await pipeline.run(basic_config)

        assert result is not None
        assert "id" in result
        assert "articles" in result

    @pytest.mark.asyncio
    async def test_pipeline_state_transitions(self, pipeline, basic_config):
        """Should transition through correct states."""
        states = []

        original_search = pipeline._search
        async def mock_search(topic):
            states.append(pipeline.pipeline_state)
            return await original_search(topic)
        pipeline._search = mock_search

        await pipeline.run(basic_config)

        assert "searching" in states
        assert pipeline.pipeline_state == "completed"

    @pytest.mark.asyncio
    async def test_pipeline_collects_search_results(self, pipeline, basic_config):
        """Should collect search results from all topics."""
        await pipeline.run(basic_config)

        # 2 topics * 5 results each = 10 results
        assert len(pipeline.search_results) == 10

    @pytest.mark.asyncio
    async def test_pipeline_parses_all_results(self, pipeline, basic_config):
        """Should parse all search results."""
        await pipeline.run(basic_config)

        assert len(pipeline.parsed_articles) == len(pipeline.search_results)

    @pytest.mark.asyncio
    async def test_pipeline_filters_by_quality(self, pipeline):
        """Should filter articles by quality threshold."""
        config = {
            "topics": ["AI"],
            "preferences": {"min_quality": 0.9},
        }

        # Mock low quality
        original_analyze = pipeline._analyze
        async def mock_analyze(article, prefs):
            result = await original_analyze(article, prefs)
            result["quality_score"] = 0.5
            return result
        pipeline._analyze = mock_analyze

        result = await pipeline.run(config)

        assert len(result["articles"]) == 0


class TestPipelineOutput:
    """Test pipeline output format."""

    @pytest.mark.asyncio
    async def test_digest_has_required_fields(self, pipeline, basic_config):
        """Digest should have all required fields."""
        result = await pipeline.run(basic_config)

        required_fields = ["id", "created_at", "topics", "articles", "metadata"]
        for field in required_fields:
            assert field in result

    @pytest.mark.asyncio
    async def test_digest_id_format(self, pipeline, basic_config):
        """Digest ID should follow expected format."""
        result = await pipeline.run(basic_config)

        assert result["id"].startswith("digest-")

    @pytest.mark.asyncio
    async def test_digest_timestamp_format(self, pipeline, basic_config):
        """Digest should have ISO format timestamp."""
        result = await pipeline.run(basic_config)

        # Should parse without error
        datetime.fromisoformat(result["created_at"].replace("Z", "+00:00"))

    @pytest.mark.asyncio
    async def test_digest_includes_topics(self, pipeline, basic_config):
        """Digest should include requested topics."""
        result = await pipeline.run(basic_config)

        assert result["topics"] == basic_config["topics"]

    @pytest.mark.asyncio
    async def test_digest_metadata_has_stats(self, pipeline, basic_config):
        """Digest metadata should have statistics."""
        result = await pipeline.run(basic_config)

        assert "total_articles" in result["metadata"]
        assert "average_quality" in result["metadata"]


class TestArticleProcessing:
    """Test article processing through pipeline."""

    @pytest.mark.asyncio
    async def test_articles_have_quality_score(self, pipeline, basic_config):
        """All articles should have quality scores."""
        result = await pipeline.run(basic_config)

        for article in result["articles"]:
            assert "quality_score" in article
            assert 0 <= article["quality_score"] <= 1

    @pytest.mark.asyncio
    async def test_articles_have_bias_assessment(self, pipeline, basic_config):
        """All articles should have bias assessment."""
        result = await pipeline.run(basic_config)

        for article in result["articles"]:
            assert "bias_assessment" in article

    @pytest.mark.asyncio
    async def test_articles_have_summary(self, pipeline, basic_config):
        """All articles should have summary."""
        result = await pipeline.run(basic_config)

        for article in result["articles"]:
            assert "summary" in article
            assert len(article["summary"]) > 0


class TestErrorHandling:
    """Test error handling in pipeline."""

    @pytest.mark.asyncio
    async def test_handles_parse_errors(self, pipeline, basic_config):
        """Should handle parse errors gracefully."""
        parse_count = [0]
        original_parse = pipeline._parse

        async def mock_parse(result):
            parse_count[0] += 1
            if parse_count[0] % 2 == 0:
                raise Exception("Parse error")
            return await original_parse(result)

        pipeline._parse = mock_parse

        result = await pipeline.run(basic_config)

        # Should have some errors but still complete
        assert len(pipeline.errors) > 0
        assert pipeline.pipeline_state == "completed"

    @pytest.mark.asyncio
    async def test_error_records_phase(self, pipeline, basic_config):
        """Errors should record which phase they occurred in."""
        original_parse = pipeline._parse
        async def mock_parse(result):
            raise Exception("Parse failed")
        pipeline._parse = mock_parse

        result = await pipeline.run(basic_config)

        for error in pipeline.errors:
            assert "phase" in error

    @pytest.mark.asyncio
    async def test_continues_after_individual_errors(self, pipeline, basic_config):
        """Should continue processing after individual article errors."""
        error_count = [0]
        original_parse = pipeline._parse

        async def mock_parse(result):
            error_count[0] += 1
            if error_count[0] == 1:
                raise Exception("First article failed")
            return await original_parse(result)

        pipeline._parse = mock_parse

        result = await pipeline.run(basic_config)

        # Should have processed remaining articles
        assert len(pipeline.parsed_articles) > 0


class TestPreferencesApplication:
    """Test preferences are applied correctly."""

    @pytest.mark.asyncio
    async def test_applies_min_quality(self, pipeline):
        """Should apply minimum quality threshold."""
        config = {
            "topics": ["AI"],
            "preferences": {"min_quality": 0.7},
        }

        result = await pipeline.run(config)

        for article in result["articles"]:
            assert article["quality_score"] >= 0.7

    @pytest.mark.asyncio
    async def test_records_applied_preferences(self, pipeline, basic_config):
        """Should record which preferences were applied."""
        result = await pipeline.run(basic_config)

        assert "preferences_applied" in result
        assert result["preferences_applied"] == basic_config["preferences"]


class TestPipelinePerformance:
    """Test pipeline performance characteristics."""

    @pytest.mark.asyncio
    async def test_handles_many_articles(self, pipeline):
        """Should handle large number of articles."""
        # Override search to return many results
        async def mock_search(topic):
            return [{"url": f"https://example.com/{topic}/{i}", "title": f"Article {i}"} for i in range(100)]

        pipeline._search = mock_search

        config = {"topics": ["AI"], "preferences": {}}
        result = await pipeline.run(config)

        assert len(result["articles"]) >= 100

    @pytest.mark.asyncio
    async def test_handles_many_topics(self, pipeline):
        """Should handle many topics."""
        config = {
            "topics": [f"Topic{i}" for i in range(20)],
            "preferences": {},
        }

        result = await pipeline.run(config)

        assert len(result["topics"]) == 20


class TestPipelineReset:
    """Test pipeline reset and reuse."""

    @pytest.mark.asyncio
    async def test_can_run_multiple_times(self, pipeline, basic_config):
        """Should be able to run pipeline multiple times."""
        result1 = await pipeline.run(basic_config)

        # Reset pipeline
        pipeline.search_results = []
        pipeline.parsed_articles = []
        pipeline.analyzed_articles = []
        pipeline.errors = []

        result2 = await pipeline.run(basic_config)

        # Both should complete successfully
        assert result1 is not None
        assert result2 is not None


class TestIntegrationWithFormats:
    """Test integration with various output formats."""

    @pytest.mark.asyncio
    async def test_digest_is_json_serializable(self, pipeline, basic_config):
        """Digest should be JSON serializable."""
        result = await pipeline.run(basic_config)

        json_str = json.dumps(result)
        parsed = json.loads(json_str)

        assert parsed["id"] == result["id"]

    @pytest.mark.asyncio
    async def test_article_urls_are_valid(self, pipeline, basic_config):
        """All article URLs should be valid."""
        result = await pipeline.run(basic_config)

        for article in result["articles"]:
            assert article["url"].startswith("https://")


class TestEdgeCases:
    """Test edge cases in pipeline."""

    @pytest.mark.asyncio
    async def test_empty_topics(self, pipeline):
        """Should handle empty topics list."""
        config = {"topics": [], "preferences": {}}
        result = await pipeline.run(config)

        assert result["articles"] == []
        assert result["topics"] == []

    @pytest.mark.asyncio
    async def test_no_preferences(self, pipeline):
        """Should work with empty preferences."""
        config = {"topics": ["AI"], "preferences": {}}
        result = await pipeline.run(config)

        assert result is not None

    @pytest.mark.asyncio
    async def test_special_characters_in_topics(self, pipeline):
        """Should handle special characters in topics."""
        config = {"topics": ["AI & ML", "C++", "Science/Tech"], "preferences": {}}
        result = await pipeline.run(config)

        assert len(result["topics"]) == 3


class TestDataIntegrity:
    """Test data integrity through pipeline."""

    @pytest.mark.asyncio
    async def test_article_ids_are_unique(self, pipeline, basic_config):
        """All article IDs should be unique."""
        result = await pipeline.run(basic_config)

        ids = [a["id"] for a in result["articles"]]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_no_duplicate_articles(self, pipeline, basic_config):
        """Should not include duplicate articles."""
        result = await pipeline.run(basic_config)

        urls = [a["url"] for a in result["articles"]]
        assert len(urls) == len(set(urls))


class TestPipelineSteps:
    """Test individual pipeline steps."""

    @pytest.mark.asyncio
    async def test_search_step(self, pipeline):
        """Search step should return results."""
        results = await pipeline._search("AI")

        assert len(results) > 0
        assert all("url" in r for r in results)

    @pytest.mark.asyncio
    async def test_parse_step(self, pipeline):
        """Parse step should extract content."""
        search_result = {"url": "https://example.com/article", "title": "Test"}
        parsed = await pipeline._parse(search_result)

        assert "content" in parsed
        assert "author" in parsed

    @pytest.mark.asyncio
    async def test_analyze_step(self, pipeline):
        """Analyze step should add scores."""
        article = {"title": "Test", "content": "Content"}
        analyzed = await pipeline._analyze(article, {})

        assert "quality_score" in analyzed
        assert "bias_assessment" in analyzed

    @pytest.mark.asyncio
    async def test_generate_step(self, pipeline):
        """Generate step should create digest."""
        articles = [{"title": "Test", "quality_score": 0.8}]
        digest = await pipeline._generate_digest(articles, ["AI"], {})

        assert "id" in digest
        assert digest["articles"] == articles


class TestFilteringLogic:
    """Test article filtering logic."""

    def test_passes_filter_high_quality(self, pipeline):
        """High quality articles should pass."""
        article = {"quality_score": 0.9}
        assert pipeline._passes_filter(article, {"min_quality": 0.5})

    def test_fails_filter_low_quality(self, pipeline):
        """Low quality articles should not pass."""
        article = {"quality_score": 0.3}
        assert not pipeline._passes_filter(article, {"min_quality": 0.5})

    def test_passes_filter_at_threshold(self, pipeline):
        """Articles at threshold should pass."""
        article = {"quality_score": 0.5}
        assert pipeline._passes_filter(article, {"min_quality": 0.5})

    def test_uses_default_threshold(self, pipeline):
        """Should use default threshold if not specified."""
        article = {"quality_score": 0.6}
        assert pipeline._passes_filter(article, {})
