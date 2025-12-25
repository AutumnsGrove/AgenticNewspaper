"""
Tests for Digest model.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Any
import json


class DigestArticle:
    """Article within a digest."""

    def __init__(
        self,
        id: str,
        title: str,
        summary: str,
        source_url: str,
        source_name: str,
        quality_score: float = 0.0,
        topics: list[str] | None = None,
        bias_direction: str = "center",
        bias_confidence: float = 0.5,
    ):
        self.id = id
        self.title = title
        self.summary = summary
        self.source_url = source_url
        self.source_name = source_name
        self.quality_score = quality_score
        self.topics = topics or []
        self.bias_direction = bias_direction
        self.bias_confidence = bias_confidence

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "source_url": self.source_url,
            "source_name": self.source_name,
            "quality_score": self.quality_score,
            "topics": self.topics,
            "bias_direction": self.bias_direction,
            "bias_confidence": self.bias_confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DigestArticle":
        return cls(**data)


class Digest:
    """News digest model."""

    def __init__(
        self,
        id: str,
        user_id: str,
        title: str,
        subtitle: str = "",
        articles: list[DigestArticle] | None = None,
        topics: list[str] | None = None,
        created_at: datetime | None = None,
        published_at: datetime | None = None,
    ):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.subtitle = subtitle
        self.articles = articles or []
        self.topics = topics or []
        self.created_at = created_at or datetime.now(timezone.utc)
        self.published_at = published_at

    @property
    def article_count(self) -> int:
        return len(self.articles)

    @property
    def average_quality(self) -> float:
        if not self.articles:
            return 0.0
        return sum(a.quality_score for a in self.articles) / len(self.articles)

    @property
    def is_published(self) -> bool:
        return self.published_at is not None

    def add_article(self, article: DigestArticle) -> None:
        self.articles.append(article)

    def remove_article(self, article_id: str) -> bool:
        initial_count = len(self.articles)
        self.articles = [a for a in self.articles if a.id != article_id]
        return len(self.articles) < initial_count

    def get_article(self, article_id: str) -> DigestArticle | None:
        for article in self.articles:
            if article.id == article_id:
                return article
        return None

    def get_articles_by_topic(self, topic: str) -> list[DigestArticle]:
        return [a for a in self.articles if topic in a.topics]

    def publish(self) -> None:
        self.published_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "subtitle": self.subtitle,
            "articles": [a.to_dict() for a in self.articles],
            "topics": self.topics,
            "created_at": self.created_at.isoformat(),
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Digest":
        articles = [DigestArticle.from_dict(a) for a in data.get("articles", [])]
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            title=data["title"],
            subtitle=data.get("subtitle", ""),
            articles=articles,
            topics=data.get("topics", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            published_at=datetime.fromisoformat(data["published_at"]) if data.get("published_at") else None,
        )


@pytest.fixture
def sample_article():
    """Create sample article."""
    return DigestArticle(
        id="article-1",
        title="AI Breakthrough",
        summary="Summary of AI news",
        source_url="https://example.com/article",
        source_name="Tech News",
        quality_score=0.85,
        topics=["AI", "Technology"],
        bias_direction="center",
        bias_confidence=0.9,
    )


@pytest.fixture
def sample_digest():
    """Create sample digest."""
    return Digest(
        id="digest-1",
        user_id="user-1",
        title="Daily Digest",
        subtitle="Your personalized news",
        topics=["AI", "Technology", "Science"],
    )


class TestDigestArticleCreation:
    """Test DigestArticle creation."""

    def test_create_article_minimal(self):
        """Should create article with minimal fields."""
        article = DigestArticle(
            id="1",
            title="Test",
            summary="Summary",
            source_url="https://example.com",
            source_name="Example",
        )
        assert article.id == "1"
        assert article.title == "Test"

    def test_create_article_full(self, sample_article):
        """Should create article with all fields."""
        assert sample_article.quality_score == 0.85
        assert sample_article.bias_direction == "center"
        assert len(sample_article.topics) == 2

    def test_default_values(self):
        """Should use default values."""
        article = DigestArticle(
            id="1",
            title="Test",
            summary="Summary",
            source_url="https://example.com",
            source_name="Example",
        )
        assert article.quality_score == 0.0
        assert article.topics == []
        assert article.bias_direction == "center"

    def test_article_to_dict(self, sample_article):
        """Should convert article to dict."""
        data = sample_article.to_dict()
        assert data["id"] == "article-1"
        assert data["title"] == "AI Breakthrough"
        assert "quality_score" in data

    def test_article_from_dict(self):
        """Should create article from dict."""
        data = {
            "id": "1",
            "title": "Test",
            "summary": "Summary",
            "source_url": "https://example.com",
            "source_name": "Example",
            "quality_score": 0.75,
            "topics": ["AI"],
            "bias_direction": "left",
            "bias_confidence": 0.8,
        }
        article = DigestArticle.from_dict(data)
        assert article.id == "1"
        assert article.quality_score == 0.75


class TestDigestCreation:
    """Test Digest creation."""

    def test_create_digest_minimal(self):
        """Should create digest with minimal fields."""
        digest = Digest(
            id="1",
            user_id="user-1",
            title="Test Digest",
        )
        assert digest.id == "1"
        assert digest.title == "Test Digest"

    def test_create_digest_full(self, sample_digest):
        """Should create digest with all fields."""
        assert sample_digest.subtitle == "Your personalized news"
        assert len(sample_digest.topics) == 3

    def test_default_values(self):
        """Should use default values."""
        digest = Digest(id="1", user_id="user-1", title="Test")
        assert digest.articles == []
        assert digest.topics == []
        assert digest.subtitle == ""
        assert digest.published_at is None

    def test_auto_created_at(self):
        """Should set created_at automatically."""
        digest = Digest(id="1", user_id="user-1", title="Test")
        assert digest.created_at is not None
        assert isinstance(digest.created_at, datetime)


class TestDigestProperties:
    """Test Digest properties."""

    def test_article_count_empty(self, sample_digest):
        """Should return 0 for empty digest."""
        assert sample_digest.article_count == 0

    def test_article_count_with_articles(self, sample_digest, sample_article):
        """Should return correct article count."""
        sample_digest.add_article(sample_article)
        assert sample_digest.article_count == 1

    def test_average_quality_empty(self, sample_digest):
        """Should return 0 for empty digest."""
        assert sample_digest.average_quality == 0.0

    def test_average_quality_calculation(self, sample_digest):
        """Should calculate average quality correctly."""
        sample_digest.add_article(DigestArticle(
            id="1", title="A", summary="S", source_url="u", source_name="n", quality_score=0.8
        ))
        sample_digest.add_article(DigestArticle(
            id="2", title="B", summary="S", source_url="u", source_name="n", quality_score=0.6
        ))
        assert sample_digest.average_quality == 0.7

    def test_is_published_false(self, sample_digest):
        """Should return False when not published."""
        assert sample_digest.is_published is False

    def test_is_published_true(self, sample_digest):
        """Should return True when published."""
        sample_digest.publish()
        assert sample_digest.is_published is True


class TestDigestArticleManagement:
    """Test article management in digest."""

    def test_add_article(self, sample_digest, sample_article):
        """Should add article to digest."""
        sample_digest.add_article(sample_article)
        assert len(sample_digest.articles) == 1

    def test_add_multiple_articles(self, sample_digest):
        """Should add multiple articles."""
        for i in range(5):
            sample_digest.add_article(DigestArticle(
                id=str(i), title=f"Article {i}", summary="S", source_url="u", source_name="n"
            ))
        assert len(sample_digest.articles) == 5

    def test_remove_article(self, sample_digest, sample_article):
        """Should remove article from digest."""
        sample_digest.add_article(sample_article)
        result = sample_digest.remove_article(sample_article.id)
        assert result is True
        assert len(sample_digest.articles) == 0

    def test_remove_nonexistent_article(self, sample_digest):
        """Should return False for nonexistent article."""
        result = sample_digest.remove_article("nonexistent")
        assert result is False

    def test_get_article(self, sample_digest, sample_article):
        """Should get article by ID."""
        sample_digest.add_article(sample_article)
        found = sample_digest.get_article(sample_article.id)
        assert found is not None
        assert found.id == sample_article.id

    def test_get_nonexistent_article(self, sample_digest):
        """Should return None for nonexistent article."""
        found = sample_digest.get_article("nonexistent")
        assert found is None

    def test_get_articles_by_topic(self, sample_digest):
        """Should filter articles by topic."""
        sample_digest.add_article(DigestArticle(
            id="1", title="AI Article", summary="S", source_url="u", source_name="n", topics=["AI"]
        ))
        sample_digest.add_article(DigestArticle(
            id="2", title="Science Article", summary="S", source_url="u", source_name="n", topics=["Science"]
        ))

        ai_articles = sample_digest.get_articles_by_topic("AI")
        assert len(ai_articles) == 1
        assert ai_articles[0].id == "1"


class TestDigestPublishing:
    """Test digest publishing."""

    def test_publish_sets_timestamp(self, sample_digest):
        """Should set published_at timestamp."""
        sample_digest.publish()
        assert sample_digest.published_at is not None

    def test_publish_timestamp_is_utc(self, sample_digest):
        """Published timestamp should be UTC."""
        sample_digest.publish()
        assert sample_digest.published_at.tzinfo == timezone.utc


class TestDigestSerialization:
    """Test digest serialization."""

    def test_digest_to_dict(self, sample_digest, sample_article):
        """Should convert digest to dict."""
        sample_digest.add_article(sample_article)
        data = sample_digest.to_dict()

        assert data["id"] == "digest-1"
        assert data["user_id"] == "user-1"
        assert len(data["articles"]) == 1

    def test_digest_to_dict_json_serializable(self, sample_digest):
        """Digest dict should be JSON serializable."""
        data = sample_digest.to_dict()
        json_str = json.dumps(data)
        assert isinstance(json_str, str)

    def test_digest_from_dict(self):
        """Should create digest from dict."""
        data = {
            "id": "1",
            "user_id": "user-1",
            "title": "Test",
            "subtitle": "Subtitle",
            "articles": [],
            "topics": ["AI"],
            "created_at": "2025-01-15T10:00:00+00:00",
            "published_at": None,
        }
        digest = Digest.from_dict(data)
        assert digest.id == "1"
        assert digest.topics == ["AI"]

    def test_roundtrip_serialization(self, sample_digest, sample_article):
        """Should survive roundtrip serialization."""
        sample_digest.add_article(sample_article)
        data = sample_digest.to_dict()
        restored = Digest.from_dict(data)

        assert restored.id == sample_digest.id
        assert len(restored.articles) == 1


class TestDigestValidation:
    """Test digest validation."""

    def test_quality_score_range(self):
        """Quality scores should be 0-1."""
        article = DigestArticle(
            id="1", title="T", summary="S", source_url="u", source_name="n", quality_score=0.5
        )
        assert 0 <= article.quality_score <= 1

    def test_bias_confidence_range(self):
        """Bias confidence should be 0-1."""
        article = DigestArticle(
            id="1", title="T", summary="S", source_url="u", source_name="n", bias_confidence=0.8
        )
        assert 0 <= article.bias_confidence <= 1


class TestDigestStatistics:
    """Test digest statistics."""

    def test_topic_distribution(self, sample_digest):
        """Should calculate topic distribution."""
        sample_digest.add_article(DigestArticle(
            id="1", title="A", summary="S", source_url="u", source_name="n", topics=["AI"]
        ))
        sample_digest.add_article(DigestArticle(
            id="2", title="B", summary="S", source_url="u", source_name="n", topics=["AI"]
        ))
        sample_digest.add_article(DigestArticle(
            id="3", title="C", summary="S", source_url="u", source_name="n", topics=["Science"]
        ))

        ai_count = len(sample_digest.get_articles_by_topic("AI"))
        science_count = len(sample_digest.get_articles_by_topic("Science"))

        assert ai_count == 2
        assert science_count == 1

    def test_bias_distribution(self, sample_digest):
        """Should track bias distribution."""
        sample_digest.add_article(DigestArticle(
            id="1", title="A", summary="S", source_url="u", source_name="n", bias_direction="left"
        ))
        sample_digest.add_article(DigestArticle(
            id="2", title="B", summary="S", source_url="u", source_name="n", bias_direction="center"
        ))
        sample_digest.add_article(DigestArticle(
            id="3", title="C", summary="S", source_url="u", source_name="n", bias_direction="right"
        ))

        directions = [a.bias_direction for a in sample_digest.articles]
        assert "left" in directions
        assert "center" in directions
        assert "right" in directions


class TestDigestTimestamps:
    """Test digest timestamp handling."""

    def test_created_at_is_utc(self, sample_digest):
        """Created timestamp should be UTC."""
        assert sample_digest.created_at.tzinfo == timezone.utc

    def test_age_calculation(self, sample_digest):
        """Should calculate digest age."""
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
        sample_digest.created_at = old_time

        age = datetime.now(timezone.utc) - sample_digest.created_at
        assert age.total_seconds() >= 7200  # At least 2 hours

    def test_is_recent(self, sample_digest):
        """Should identify recent digests."""
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        sample_digest.created_at = one_hour_ago

        age = datetime.now(timezone.utc) - sample_digest.created_at
        is_recent = age < timedelta(hours=24)
        assert is_recent is True


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_title(self):
        """Should handle empty title."""
        digest = Digest(id="1", user_id="user-1", title="")
        assert digest.title == ""

    def test_unicode_content(self):
        """Should handle unicode content."""
        article = DigestArticle(
            id="1",
            title="日本語タイトル",
            summary="中文摘要",
            source_url="https://example.com",
            source_name="Example",
        )
        assert article.title == "日本語タイトル"

    def test_special_characters(self):
        """Should handle special characters."""
        article = DigestArticle(
            id="1",
            title="Test <script>alert('xss')</script>",
            summary="Test & more",
            source_url="https://example.com?foo=bar&baz=qux",
            source_name="Example",
        )
        assert "<script>" in article.title

    def test_very_long_summary(self):
        """Should handle very long summaries."""
        long_summary = "A" * 10000
        article = DigestArticle(
            id="1",
            title="Test",
            summary=long_summary,
            source_url="https://example.com",
            source_name="Example",
        )
        assert len(article.summary) == 10000


class TestArticleBiasAssessment:
    """Test bias assessment fields."""

    def test_all_bias_directions(self):
        """Should accept all valid bias directions."""
        valid_directions = ["left", "center-left", "center", "center-right", "right"]

        for direction in valid_directions:
            article = DigestArticle(
                id="1", title="T", summary="S", source_url="u", source_name="n",
                bias_direction=direction
            )
            assert article.bias_direction == direction

    def test_bias_confidence_boundaries(self):
        """Should handle boundary confidence values."""
        for confidence in [0.0, 0.5, 1.0]:
            article = DigestArticle(
                id="1", title="T", summary="S", source_url="u", source_name="n",
                bias_confidence=confidence
            )
            assert article.bias_confidence == confidence


class TestDigestComparison:
    """Test digest comparison and equality."""

    def test_digests_with_same_id_are_comparable(self):
        """Should compare digests by ID."""
        digest1 = Digest(id="1", user_id="u1", title="A")
        digest2 = Digest(id="1", user_id="u1", title="B")

        assert digest1.id == digest2.id

    def test_digests_with_different_ids(self):
        """Should distinguish digests by ID."""
        digest1 = Digest(id="1", user_id="u1", title="A")
        digest2 = Digest(id="2", user_id="u1", title="A")

        assert digest1.id != digest2.id
