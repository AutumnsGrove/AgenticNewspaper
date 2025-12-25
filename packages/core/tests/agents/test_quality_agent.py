"""
Tests for the Quality Agent.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from src.agents.tier2_reasoning.quality_agent import (
    QualityAgent,
    TopicConfig,
)
from src.models.article import (
    QualityAnalysis,
    ContentType,
    ParsedArticle,
)
from src.providers.base import LLMResponse


# ============================================================================
# QualityAnalysis Tests
# ============================================================================


class TestQualityAnalysis:
    """Tests for the QualityAnalysis dataclass."""

    def test_create_analysis(self):
        """Test creating a quality analysis."""
        analysis = QualityAnalysis(
            relevance_score=0.85,
            quality_score=0.78,
            novelty_score=0.72,
            depth_score=0.80,
            credibility_score=0.90,
        )
        assert analysis.relevance_score == 0.85
        assert analysis.quality_score == 0.78
        assert analysis.novelty_score == 0.72

    def test_analysis_with_content(self):
        """Test analysis with extracted content."""
        analysis = QualityAnalysis(
            relevance_score=0.9,
            quality_score=0.85,
            key_points=["Point 1", "Point 2", "Point 3"],
            why_matters="This is important because...",
            implications=["Implication 1", "Implication 2"],  # Not technical_insights
        )
        assert len(analysis.key_points) == 3
        assert analysis.why_matters is not None
        assert len(analysis.implications) == 2

    def test_analysis_default_values(self):
        """Test analysis default values."""
        analysis = QualityAnalysis()
        assert analysis.relevance_score == 0.0
        assert analysis.quality_score == 0.0
        assert analysis.key_points == []
        assert analysis.skip_reason is None

    @pytest.mark.parametrize(
        "score",
        [0.0, 0.25, 0.5, 0.75, 1.0],
    )
    def test_valid_score_range(self, score):
        """Test that scores are in valid range."""
        analysis = QualityAnalysis(
            relevance_score=score,
            quality_score=score,
            novelty_score=score,
        )
        assert 0 <= analysis.relevance_score <= 1
        assert 0 <= analysis.quality_score <= 1

    def test_analysis_with_skip_reason(self):
        """Test analysis with skip reason."""
        analysis = QualityAnalysis(
            relevance_score=0.2,
            quality_score=0.3,
            skip_reason="Content is too short and lacks substance.",
        )
        assert analysis.skip_reason is not None


# ============================================================================
# ContentType Tests
# ============================================================================


class TestContentType:
    """Tests for ContentType enum."""

    def test_research_type(self):
        """Test research content type."""
        assert ContentType.RESEARCH.value == "research"

    def test_news_type(self):
        """Test news content type."""
        assert ContentType.NEWS.value == "news"

    def test_opinion_type(self):
        """Test opinion content type."""
        assert ContentType.OPINION.value == "opinion"

    def test_analysis_type(self):
        """Test analysis content type (no TUTORIAL)."""
        assert ContentType.ANALYSIS.value == "analysis"

    def test_all_types_defined(self):
        """Test that all expected types are defined."""
        types = [t.value for t in ContentType]
        assert "research" in types
        assert "news" in types
        assert "opinion" in types
        assert "analysis" in types


# ============================================================================
# Quality Agent Initialization Tests
# ============================================================================


class TestQualityAgentInit:
    """Tests for Quality Agent initialization."""

    def test_init_with_provider(self):
        """Test initialization with provider."""
        mock_provider = MagicMock()
        agent = QualityAgent(provider=mock_provider)
        assert agent.provider == mock_provider

    def test_init_with_config(self):
        """Test initialization with topic configuration."""
        mock_provider = MagicMock()
        config = TopicConfig(name="AI", min_quality=0.6, prefer_technical=True)
        agent = QualityAgent(provider=mock_provider, default_config=config)
        assert agent.default_config.name == "AI"
        assert agent.default_config.min_quality == 0.6


# ============================================================================
# Helper Functions
# ============================================================================


def _make_article(
    title: str = "Test Article",
    content: str = "Test content for the article.",
    source: str = "test.com",
) -> ParsedArticle:
    """Helper to create test articles."""
    return ParsedArticle(
        article_id="test-001",
        url=f"https://{source}/article",
        title=title,
        content=content,
        source=source,
    )


def _make_response(data: dict) -> LLMResponse:
    """Create a mock LLM response with JSON content."""
    return LLMResponse(
        content=json.dumps(data),
        model="test-model",
        provider="test",
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        response_time_seconds=1.0,
    )


# ============================================================================
# Quality Agent Analyze Tests
# ============================================================================


class TestQualityAgentAnalyze:
    """Tests for Quality Agent analyze method."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.complete = AsyncMock()
        provider.get_stats = MagicMock(return_value={})
        return provider

    @pytest.fixture
    def agent(self, mock_provider):
        """Create a Quality Agent instance."""
        return QualityAgent(provider=mock_provider)

    @pytest.fixture
    def sample_article(self):
        """Create a sample article for testing."""
        return _make_article(
            title="AI Breakthrough: New Model Achieves Record Performance",
            content="""
            Researchers have developed a new AI model that achieves state-of-the-art
            performance on multiple benchmarks. The model uses a novel architecture
            that combines transformer attention with sparse mixture-of-experts.

            Key findings include:
            - 30% improvement in reasoning tasks
            - 50% reduction in inference costs
            - Applicable to multiple domains

            The implications for the field are significant, as this approach
            could enable more efficient deployment of large language models.
            """,
            source="arxiv.org",
        )

    @pytest.mark.asyncio
    async def test_analyze_returns_analysis(self, agent, mock_provider, sample_article):
        """Test that analyze returns a QualityAnalysis."""
        mock_provider.complete.return_value = _make_response({
            "relevance_score": 0.85,
            "quality_score": 0.78,
            "novelty_score": 0.72,
            "depth_score": 0.80,
            "credibility_score": 0.90,
            "key_points": ["Point 1", "Point 2"],
            "why_matters": "Important for AI development",
            "content_type": "research",
            "should_include": True,
        })

        analysis = await agent.analyze(sample_article)
        assert isinstance(analysis, QualityAnalysis)
        assert analysis.relevance_score == 0.85

    @pytest.mark.asyncio
    async def test_analyze_with_topic_config(self, agent, mock_provider, sample_article):
        """Test analysis with topic configuration."""
        mock_provider.complete.return_value = _make_response({
            "relevance_score": 0.90,
            "quality_score": 0.85,
            "should_include": True,
        })

        topic = TopicConfig(name="AI", keywords=["artificial intelligence"])
        analysis = await agent.analyze(sample_article, topic_config=topic)
        assert analysis is not None

    @pytest.mark.asyncio
    async def test_analyze_extracts_key_points(self, agent, mock_provider, sample_article):
        """Test that analysis extracts key points."""
        mock_provider.complete.return_value = _make_response({
            "relevance_score": 0.8,
            "quality_score": 0.8,
            "key_points": [
                "30% improvement in reasoning",
                "50% cost reduction",
                "Multi-domain applicability",
            ],
            "should_include": True,
        })

        analysis = await agent.analyze(sample_article)
        assert len(analysis.key_points) == 3

    @pytest.mark.asyncio
    async def test_analyze_identifies_content_type(self, agent, mock_provider, sample_article):
        """Test that analysis identifies content type."""
        mock_provider.complete.return_value = _make_response({
            "relevance_score": 0.8,
            "quality_score": 0.8,
            "content_type": "RESEARCH",
            "should_include": True,
        })

        analysis = await agent.analyze(sample_article)
        assert analysis.content_type == ContentType.RESEARCH

    @pytest.mark.asyncio
    async def test_analyze_handles_low_quality(self, agent, mock_provider):
        """Test analysis of low-quality content."""
        low_quality_article = _make_article(
            title="Click Here!!!",
            content="Buy now! Limited offer!",
            source="spam.com",
        )

        mock_provider.complete.return_value = _make_response({
            "relevance_score": 0.1,
            "quality_score": 0.1,
            "skip_reason": "Appears to be spam or promotional content.",
            "should_include": False,
        })

        analysis = await agent.analyze(low_quality_article)
        assert analysis.quality_score < 0.5
        assert analysis.skip_reason is not None


# ============================================================================
# Quality Scoring Tests
# ============================================================================


class TestQualityScoring:
    """Tests for quality scoring logic."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.complete = AsyncMock()
        provider.get_stats = MagicMock(return_value={})
        return provider

    @pytest.fixture
    def agent(self, mock_provider):
        """Create a Quality Agent instance."""
        return QualityAgent(provider=mock_provider)

    @pytest.mark.asyncio
    async def test_high_quality_research_paper(self, agent, mock_provider):
        """Test scoring of high-quality research paper."""
        article = _make_article(
            title="Novel Approach to Neural Architecture Search",
            content="We present a comprehensive study..." * 100,
            source="arxiv.org",
        )

        mock_provider.complete.return_value = _make_response({
            "relevance_score": 0.95,
            "quality_score": 0.92,
            "novelty_score": 0.88,
            "credibility_score": 0.95,
            "content_type": "RESEARCH",
            "should_include": True,
        })

        analysis = await agent.analyze(article)
        assert analysis.quality_score >= 0.8

    @pytest.mark.asyncio
    async def test_news_article_scoring(self, agent, mock_provider):
        """Test scoring of news article."""
        article = _make_article(
            title="Company Announces New Product",
            content="Today, the company revealed..." * 50,
            source="techcrunch.com",
        )

        mock_provider.complete.return_value = _make_response({
            "relevance_score": 0.75,
            "quality_score": 0.70,
            "novelty_score": 0.60,
            "content_type": "NEWS",
            "should_include": True,
        })

        analysis = await agent.analyze(article)
        assert analysis.content_type == ContentType.NEWS

    @pytest.mark.asyncio
    async def test_opinion_piece_scoring(self, agent, mock_provider):
        """Test scoring of opinion piece."""
        article = _make_article(
            title="Why AI Will Change Everything",
            content="In my opinion..." * 50,
            source="medium.com",
        )

        mock_provider.complete.return_value = _make_response({
            "relevance_score": 0.65,
            "quality_score": 0.55,
            "content_type": "OPINION",
            "should_include": True,
        })

        analysis = await agent.analyze(article)
        assert analysis.content_type == ContentType.OPINION


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestQualityAgentErrors:
    """Tests for Quality Agent error handling."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.complete = AsyncMock()
        provider.get_stats = MagicMock(return_value={})
        return provider

    @pytest.fixture
    def agent(self, mock_provider):
        """Create a Quality Agent instance."""
        return QualityAgent(provider=mock_provider)

    @pytest.mark.asyncio
    async def test_handles_provider_error(self, agent, mock_provider):
        """Test handling of provider errors."""
        mock_provider.complete.side_effect = Exception("API Error")

        article = _make_article()

        with pytest.raises(Exception):
            await agent.analyze(article)

    @pytest.mark.asyncio
    async def test_handles_invalid_response(self, agent, mock_provider):
        """Test handling of invalid LLM response."""
        mock_provider.complete.return_value = LLMResponse(
            content='{"invalid": "response"}',
            model="test",
            provider="test",
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.0,
            response_time_seconds=0.5,
        )

        article = _make_article()
        analysis = await agent.analyze(article)
        # Should use default values
        assert analysis.relevance_score == 0.5  # Default on parse error

    @pytest.mark.asyncio
    async def test_handles_empty_content(self, agent, mock_provider):
        """Test handling of empty article content."""
        mock_provider.complete.return_value = _make_response({
            "relevance_score": 0.0,
            "quality_score": 0.0,
            "skip_reason": "No content to analyze",
            "should_include": False,
        })

        article = _make_article(title="", content="")
        analysis = await agent.analyze(article)
        assert analysis.skip_reason is not None


# ============================================================================
# Integration Tests
# ============================================================================


class TestQualityAgentIntegration:
    """Integration tests for Quality Agent."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.complete = AsyncMock()
        provider.get_stats = MagicMock(return_value={})
        return provider

    @pytest.fixture
    def agent(self, mock_provider):
        """Create a Quality Agent instance."""
        return QualityAgent(provider=mock_provider)

    @pytest.mark.asyncio
    async def test_batch_analyze(self, agent, mock_provider):
        """Test analyzing multiple articles via batch_analyze."""
        articles = [
            _make_article(title=f"Article {i}", content=f"Content {i}" * 50)
            for i in range(5)
        ]

        mock_provider.complete.return_value = _make_response({
            "relevance_score": 0.8,
            "quality_score": 0.75,
            "should_include": True,
        })

        results = await agent.batch_analyze(articles)
        assert len(results) == 5
        assert all(isinstance(r, QualityAnalysis) for r in results)

    @pytest.mark.asyncio
    async def test_analyze_with_config(self, agent, mock_provider):
        """Test analysis respects topic configuration."""
        config = TopicConfig(
            name="AI",
            keywords=["AI", "ML"],
            min_quality=0.7,
        )
        agent_with_config = QualityAgent(provider=mock_provider, default_config=config)

        mock_provider.complete.return_value = _make_response({
            "relevance_score": 0.9,
            "quality_score": 0.85,
            "should_include": True,
        })

        article = _make_article(title="AI News", content="Content about AI")
        analysis = await agent_with_config.analyze(article)

        assert analysis.quality_score >= 0.7
