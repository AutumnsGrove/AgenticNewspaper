"""
Tests for the Quality Agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from src.agents.tier2_reasoning.quality_agent import (
    QualityAgent,
    QualityAnalysis,
    ContentType,
)


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
            technical_insights=["Insight 1", "Insight 2"],
        )
        assert len(analysis.key_points) == 3
        assert analysis.why_matters is not None
        assert len(analysis.technical_insights) == 2

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

    def test_tutorial_type(self):
        """Test tutorial content type."""
        assert ContentType.TUTORIAL.value == "tutorial"

    def test_all_types_defined(self):
        """Test that all expected types are defined."""
        types = [t.value for t in ContentType]
        assert "research" in types
        assert "news" in types
        assert "opinion" in types


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

    def test_init_with_preferences(self):
        """Test initialization with user preferences."""
        mock_provider = MagicMock()
        preferences = {"min_quality": 0.6, "technical_depth": 4}
        agent = QualityAgent(provider=mock_provider, preferences=preferences)
        assert agent.preferences == preferences


# ============================================================================
# Quality Agent Evaluation Tests
# ============================================================================


class TestQualityAgentEvaluate:
    """Tests for Quality Agent evaluation method."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.complete_json = AsyncMock()
        return provider

    @pytest.fixture
    def agent(self, mock_provider):
        """Create a Quality Agent instance."""
        return QualityAgent(provider=mock_provider)

    @pytest.fixture
    def sample_article(self):
        """Create a sample article for testing."""
        return {
            "url": "https://example.com/article",
            "title": "AI Breakthrough: New Model Achieves Record Performance",
            "content": """
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
            "source": "arxiv.org",
            "word_count": 150,
        }

    @pytest.mark.asyncio
    async def test_evaluate_returns_analysis(self, agent, mock_provider, sample_article):
        """Test that evaluate returns a QualityAnalysis."""
        mock_provider.complete_json.return_value = {
            "relevance_score": 0.85,
            "quality_score": 0.78,
            "novelty_score": 0.72,
            "depth_score": 0.80,
            "credibility_score": 0.90,
            "key_points": ["Point 1", "Point 2"],
            "why_matters": "Important for AI development",
            "content_type": "research",
        }

        analysis = await agent.evaluate(sample_article)
        assert isinstance(analysis, QualityAnalysis)
        assert analysis.relevance_score == 0.85

    @pytest.mark.asyncio
    async def test_evaluate_with_topic_context(self, agent, mock_provider, sample_article):
        """Test evaluation with topic context."""
        mock_provider.complete_json.return_value = {
            "relevance_score": 0.90,
            "quality_score": 0.85,
        }

        topic = {"name": "AI", "keywords": ["artificial intelligence"]}
        analysis = await agent.evaluate(sample_article, topic=topic)
        assert analysis is not None

    @pytest.mark.asyncio
    async def test_evaluate_extracts_key_points(self, agent, mock_provider, sample_article):
        """Test that evaluation extracts key points."""
        mock_provider.complete_json.return_value = {
            "relevance_score": 0.8,
            "quality_score": 0.8,
            "key_points": [
                "30% improvement in reasoning",
                "50% cost reduction",
                "Multi-domain applicability",
            ],
        }

        analysis = await agent.evaluate(sample_article)
        assert len(analysis.key_points) == 3

    @pytest.mark.asyncio
    async def test_evaluate_identifies_content_type(self, agent, mock_provider, sample_article):
        """Test that evaluation identifies content type."""
        mock_provider.complete_json.return_value = {
            "relevance_score": 0.8,
            "quality_score": 0.8,
            "content_type": "research",
        }

        analysis = await agent.evaluate(sample_article)
        assert analysis.content_type == ContentType.RESEARCH

    @pytest.mark.asyncio
    async def test_evaluate_handles_low_quality(self, agent, mock_provider):
        """Test evaluation of low-quality content."""
        low_quality_article = {
            "url": "https://example.com/spam",
            "title": "Click Here!!!",
            "content": "Buy now! Limited offer!",
            "source": "spam.com",
            "word_count": 10,
        }

        mock_provider.complete_json.return_value = {
            "relevance_score": 0.1,
            "quality_score": 0.1,
            "skip_reason": "Appears to be spam or promotional content.",
        }

        analysis = await agent.evaluate(low_quality_article)
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
        provider.complete_json = AsyncMock()
        return provider

    @pytest.fixture
    def agent(self, mock_provider):
        """Create a Quality Agent instance."""
        return QualityAgent(provider=mock_provider)

    @pytest.mark.asyncio
    async def test_high_quality_research_paper(self, agent, mock_provider):
        """Test scoring of high-quality research paper."""
        article = {
            "title": "Novel Approach to Neural Architecture Search",
            "content": "We present a comprehensive study..." * 100,
            "source": "arxiv.org",
            "word_count": 3000,
        }

        mock_provider.complete_json.return_value = {
            "relevance_score": 0.95,
            "quality_score": 0.92,
            "novelty_score": 0.88,
            "credibility_score": 0.95,
        }

        analysis = await agent.evaluate(article)
        assert analysis.quality_score >= 0.8

    @pytest.mark.asyncio
    async def test_news_article_scoring(self, agent, mock_provider):
        """Test scoring of news article."""
        article = {
            "title": "Company Announces New Product",
            "content": "Today, the company revealed..." * 50,
            "source": "techcrunch.com",
            "word_count": 500,
        }

        mock_provider.complete_json.return_value = {
            "relevance_score": 0.75,
            "quality_score": 0.70,
            "novelty_score": 0.60,
            "content_type": "news",
        }

        analysis = await agent.evaluate(article)
        assert analysis.content_type == ContentType.NEWS

    @pytest.mark.asyncio
    async def test_opinion_piece_scoring(self, agent, mock_provider):
        """Test scoring of opinion piece."""
        article = {
            "title": "Why AI Will Change Everything",
            "content": "In my opinion..." * 50,
            "source": "medium.com",
            "word_count": 800,
        }

        mock_provider.complete_json.return_value = {
            "relevance_score": 0.65,
            "quality_score": 0.55,
            "content_type": "opinion",
        }

        analysis = await agent.evaluate(article)
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
        provider.complete_json = AsyncMock()
        return provider

    @pytest.fixture
    def agent(self, mock_provider):
        """Create a Quality Agent instance."""
        return QualityAgent(provider=mock_provider)

    @pytest.mark.asyncio
    async def test_handles_provider_error(self, agent, mock_provider):
        """Test handling of provider errors."""
        mock_provider.complete_json.side_effect = Exception("API Error")

        article = {"title": "Test", "content": "Content", "source": "test.com"}

        with pytest.raises(Exception):
            await agent.evaluate(article)

    @pytest.mark.asyncio
    async def test_handles_invalid_response(self, agent, mock_provider):
        """Test handling of invalid LLM response."""
        mock_provider.complete_json.return_value = {
            "invalid": "response",
        }

        article = {"title": "Test", "content": "Content", "source": "test.com"}
        analysis = await agent.evaluate(article)
        # Should use default values
        assert analysis.relevance_score == 0.0

    @pytest.mark.asyncio
    async def test_handles_empty_content(self, agent, mock_provider):
        """Test handling of empty article content."""
        mock_provider.complete_json.return_value = {
            "relevance_score": 0.0,
            "quality_score": 0.0,
            "skip_reason": "No content to analyze",
        }

        article = {"title": "", "content": "", "source": "test.com"}
        analysis = await agent.evaluate(article)
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
        provider.complete_json = AsyncMock()
        return provider

    @pytest.fixture
    def agent(self, mock_provider):
        """Create a Quality Agent instance."""
        return QualityAgent(provider=mock_provider)

    @pytest.mark.asyncio
    async def test_batch_evaluation(self, agent, mock_provider):
        """Test evaluating multiple articles."""
        articles = [
            {"title": f"Article {i}", "content": f"Content {i}" * 50, "source": "test.com"}
            for i in range(5)
        ]

        mock_provider.complete_json.return_value = {
            "relevance_score": 0.8,
            "quality_score": 0.75,
        }

        results = []
        for article in articles:
            result = await agent.evaluate(article)
            results.append(result)

        assert len(results) == 5
        assert all(isinstance(r, QualityAnalysis) for r in results)

    @pytest.mark.asyncio
    async def test_evaluation_with_preferences(self, agent, mock_provider):
        """Test evaluation respects user preferences."""
        agent.preferences = {
            "min_quality": 0.7,
            "preferred_topics": ["AI", "ML"],
        }

        mock_provider.complete_json.return_value = {
            "relevance_score": 0.9,
            "quality_score": 0.85,
        }

        article = {"title": "AI News", "content": "Content about AI", "source": "test.com"}
        analysis = await agent.evaluate(article)

        assert analysis.quality_score >= 0.7
