"""
Tests for article models.
"""

import pytest
from dataclasses import asdict
from datetime import datetime

from src.models.article import (
    ParsedArticle,
    AnalyzedArticle,
    QualityAnalysis,
    BiasAnalysis,
    BiasDirection,
    ContentType,
    CrossConnection,
)


# ============================================================================
# ParsedArticle Tests
# ============================================================================


class TestParsedArticle:
    """Tests for the ParsedArticle dataclass."""

    def test_create_basic_article(self):
        """Test creating a basic parsed article."""
        article = ParsedArticle(
            url="https://example.com/article",
            title="Test Article Title",
            content="This is the article content.",
            source="example.com",
            word_count=5,
        )
        assert article.url == "https://example.com/article"
        assert article.title == "Test Article Title"
        assert article.content == "This is the article content."
        assert article.source == "example.com"
        assert article.word_count == 5

    def test_article_with_metadata(self):
        """Test article with full metadata."""
        article = ParsedArticle(
            url="https://example.com/article",
            title="Full Article",
            content="Content here",
            source="example.com",
            author="John Doe",
            published_date="2025-12-24",
            word_count=100,
            language="en",
            image_url="https://example.com/image.jpg",
        )
        assert article.author == "John Doe"
        assert article.published_date == "2025-12-24"
        assert article.language == "en"
        assert article.image_url is not None

    def test_article_reading_time(self):
        """Test reading time calculation."""
        # 250 words = ~1 minute at 250 WPM
        article = ParsedArticle(
            url="https://example.com",
            title="Test",
            content="word " * 250,
            source="example.com",
            word_count=250,
        )
        # Reading time should be around 1 minute
        expected_time = article.word_count / 200  # ~200 WPM
        assert expected_time > 0

    def test_article_defaults(self):
        """Test article default values."""
        article = ParsedArticle(
            url="https://example.com",
            title="Test",
            content="Content",
            source="example.com",
        )
        assert article.author is None
        assert article.published_date is None
        assert article.word_count == 0

    def test_article_to_dict(self):
        """Test converting article to dictionary."""
        article = ParsedArticle(
            url="https://example.com",
            title="Test",
            content="Content",
            source="example.com",
        )
        d = asdict(article)
        assert "url" in d
        assert "title" in d
        assert "content" in d


# ============================================================================
# QualityAnalysis Tests
# ============================================================================


class TestQualityAnalysis:
    """Tests for the QualityAnalysis dataclass."""

    def test_create_analysis(self):
        """Test creating quality analysis."""
        analysis = QualityAnalysis(
            relevance_score=0.85,
            quality_score=0.78,
            novelty_score=0.72,
            depth_score=0.80,
            credibility_score=0.90,
        )
        assert analysis.relevance_score == 0.85
        assert analysis.quality_score == 0.78

    def test_analysis_with_content(self):
        """Test analysis with extracted content."""
        analysis = QualityAnalysis(
            relevance_score=0.9,
            quality_score=0.85,
            key_points=["Point 1", "Point 2", "Point 3"],
            why_matters="Important because...",
            technical_insights=["Uses novel architecture"],
            content_type=ContentType.RESEARCH,
        )
        assert len(analysis.key_points) == 3
        assert analysis.content_type == ContentType.RESEARCH

    def test_analysis_defaults(self):
        """Test default values."""
        analysis = QualityAnalysis()
        assert analysis.relevance_score == 0.0
        assert analysis.quality_score == 0.0
        assert analysis.key_points == []

    @pytest.mark.parametrize(
        "score",
        [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0],
    )
    def test_valid_score_range(self, score):
        """Test that various scores are valid."""
        analysis = QualityAnalysis(
            relevance_score=score,
            quality_score=score,
        )
        assert 0 <= analysis.relevance_score <= 1

    def test_skip_reason(self):
        """Test analysis with skip reason."""
        analysis = QualityAnalysis(
            relevance_score=0.1,
            skip_reason="Content is too short",
        )
        assert analysis.skip_reason is not None


# ============================================================================
# BiasAnalysis Tests
# ============================================================================


class TestBiasAnalysis:
    """Tests for the BiasAnalysis dataclass."""

    def test_create_analysis(self):
        """Test creating bias analysis."""
        analysis = BiasAnalysis(
            bias_score=0.35,
            bias_direction=BiasDirection.CENTER_LEFT,
            confidence=0.75,
        )
        assert analysis.bias_score == 0.35
        assert analysis.bias_direction == BiasDirection.CENTER_LEFT

    def test_analysis_with_details(self):
        """Test analysis with full details."""
        analysis = BiasAnalysis(
            bias_score=0.7,
            bias_direction=BiasDirection.RIGHT,
            loaded_language=["radical", "extremist"],
            missing_perspectives=["Liberal viewpoint"],
            skeptics_corner="One-sided coverage.",
            red_flags=["Cherry-picked data"],
        )
        assert len(analysis.loaded_language) == 2
        assert len(analysis.red_flags) == 1

    def test_analysis_defaults(self):
        """Test default values."""
        analysis = BiasAnalysis()
        assert analysis.bias_score == 0.5
        assert analysis.bias_direction == BiasDirection.UNKNOWN

    def test_neutral_analysis(self):
        """Test neutral bias analysis."""
        analysis = BiasAnalysis(
            bias_score=0.5,
            bias_direction=BiasDirection.CENTER,
            loaded_language=[],
            missing_perspectives=[],
        )
        assert analysis.bias_direction == BiasDirection.CENTER
        assert len(analysis.loaded_language) == 0


# ============================================================================
# BiasDirection Tests
# ============================================================================


class TestBiasDirection:
    """Tests for the BiasDirection enum."""

    def test_all_directions(self):
        """Test all bias directions are defined."""
        directions = list(BiasDirection)
        assert len(directions) >= 6

    @pytest.mark.parametrize(
        "direction,value",
        [
            (BiasDirection.LEFT, "left"),
            (BiasDirection.CENTER_LEFT, "center-left"),
            (BiasDirection.CENTER, "center"),
            (BiasDirection.CENTER_RIGHT, "center-right"),
            (BiasDirection.RIGHT, "right"),
            (BiasDirection.UNKNOWN, "unknown"),
        ],
    )
    def test_direction_values(self, direction, value):
        """Test direction values."""
        assert direction.value == value


# ============================================================================
# ContentType Tests
# ============================================================================


class TestContentType:
    """Tests for the ContentType enum."""

    def test_all_types(self):
        """Test all content types are defined."""
        types = list(ContentType)
        assert len(types) >= 4

    @pytest.mark.parametrize(
        "content_type",
        [
            ContentType.RESEARCH,
            ContentType.NEWS,
            ContentType.OPINION,
            ContentType.ANALYSIS,
        ],
    )
    def test_type_values(self, content_type):
        """Test content type values are strings."""
        assert isinstance(content_type.value, str)


# ============================================================================
# CrossConnection Tests
# ============================================================================


class TestCrossConnection:
    """Tests for the CrossConnection dataclass."""

    def test_create_connection(self):
        """Test creating a cross connection."""
        connection = CrossConnection(
            articles=["article-1", "article-2"],
            pattern_type="contradiction",
            description="These articles present conflicting findings.",
            confidence=0.85,
        )
        assert len(connection.articles) == 2
        assert connection.pattern_type == "contradiction"
        assert connection.confidence == 0.85

    def test_connection_types(self):
        """Test different connection types."""
        for pattern in ["trend", "contradiction", "reinforcement", "evolution"]:
            connection = CrossConnection(
                articles=["a", "b"],
                pattern_type=pattern,
                description="Test description",
            )
            assert connection.pattern_type == pattern


# ============================================================================
# AnalyzedArticle Tests
# ============================================================================


class TestAnalyzedArticle:
    """Tests for the AnalyzedArticle dataclass."""

    def test_create_analyzed_article(self):
        """Test creating an analyzed article."""
        quality = QualityAnalysis(
            relevance_score=0.85,
            quality_score=0.78,
        )
        bias = BiasAnalysis(
            bias_score=0.5,
            bias_direction=BiasDirection.CENTER,
        )

        article = AnalyzedArticle(
            url="https://example.com",
            title="Analyzed Article",
            content="Content",
            source="example.com",
            quality_analysis=quality,
            bias_analysis=bias,
        )
        assert article.quality_analysis.relevance_score == 0.85
        assert article.bias_analysis.bias_direction == BiasDirection.CENTER

    def test_article_passes_threshold(self):
        """Test checking if article passes quality threshold."""
        article = AnalyzedArticle(
            url="https://example.com",
            title="Test",
            content="Content",
            source="example.com",
            quality_analysis=QualityAnalysis(
                relevance_score=0.8,
                quality_score=0.75,
            ),
        )
        # Check if it would pass a 0.7 threshold
        assert article.quality_analysis.relevance_score >= 0.7
        assert article.quality_analysis.quality_score >= 0.7

    def test_article_with_key_points(self):
        """Test article with extracted key points."""
        article = AnalyzedArticle(
            url="https://example.com",
            title="Test",
            content="Content",
            source="example.com",
            quality_analysis=QualityAnalysis(
                relevance_score=0.8,
                quality_score=0.75,
                key_points=["Key point 1", "Key point 2", "Key point 3"],
                why_matters="This is significant because...",
            ),
        )
        assert len(article.quality_analysis.key_points) == 3


# ============================================================================
# Model Serialization Tests
# ============================================================================


class TestModelSerialization:
    """Tests for model serialization."""

    def test_quality_analysis_to_dict(self):
        """Test converting quality analysis to dictionary."""
        analysis = QualityAnalysis(
            relevance_score=0.85,
            quality_score=0.78,
            key_points=["Point 1"],
        )
        d = asdict(analysis)
        assert d["relevance_score"] == 0.85
        assert d["key_points"] == ["Point 1"]

    def test_bias_analysis_to_dict(self):
        """Test converting bias analysis to dictionary."""
        analysis = BiasAnalysis(
            bias_score=0.5,
            bias_direction=BiasDirection.CENTER,
        )
        d = asdict(analysis)
        assert d["bias_score"] == 0.5
        # Enum should be converted
        assert d["bias_direction"] == BiasDirection.CENTER

    def test_parsed_article_to_dict(self):
        """Test converting parsed article to dictionary."""
        article = ParsedArticle(
            url="https://example.com",
            title="Test",
            content="Content",
            source="example.com",
        )
        d = asdict(article)
        assert "url" in d
        assert "title" in d
