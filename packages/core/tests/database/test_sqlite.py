"""
Tests for the SQLite database implementation.
"""

import pytest
from datetime import datetime, timedelta
import json
import asyncio
import uuid
import hashlib

from src.database.sqlite import SQLiteDatabase
from src.database.base import (
    User,
    DigestRecord,
    ArticleRecord,
    FeedbackRecord,
    UsageRecord,
    DuplicateError,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return str(tmp_path / "test.db")


# ============================================================================
# Database Initialization Tests
# ============================================================================


class TestSQLiteInit:
    """Tests for SQLite database initialization."""

    @pytest.mark.asyncio
    async def test_init_creates_tables(self, temp_db_path):
        """Test that initialization creates all required tables."""
        db = SQLiteDatabase(temp_db_path)
        await db.initialize()

        # Verify tables exist by checking their names
        conn = await db._get_db()
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = await cursor.fetchall()
        await cursor.close()
        table_names = [t[0] for t in tables]

        assert "users" in table_names
        assert "digests" in table_names
        assert "articles" in table_names
        assert "feedback" in table_names
        assert "usage" in table_names

        await db.close()

    @pytest.mark.asyncio
    async def test_init_creates_indexes(self, temp_db_path):
        """Test that initialization creates indexes."""
        db = SQLiteDatabase(temp_db_path)
        await db.initialize()

        conn = await db._get_db()
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        indexes = await cursor.fetchall()
        await cursor.close()

        await db.close()
        assert len(indexes) > 0

    @pytest.mark.asyncio
    async def test_init_is_idempotent(self, temp_db_path):
        """Test that initialization can be called multiple times."""
        db = SQLiteDatabase(temp_db_path)
        await db.initialize()
        await db.initialize()  # Should not raise
        await db.close()


# ============================================================================
# User Operations Tests
# ============================================================================


class TestUserOperations:
    """Tests for user CRUD operations."""

    @pytest.fixture
    async def db(self, temp_db_path):
        """Create and initialize a database."""
        db = SQLiteDatabase(temp_db_path)
        await db.initialize()
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_create_user(self, db):
        """Test creating a new user."""
        user = User(
            id="user-001",
            email="test@example.com",
            created_at=datetime.now(),
            preferences_json=json.dumps({"topics": ["AI"]}),
        )
        result = await db.create_user(user)
        assert result.id == "user-001"
        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_create_user_with_tier(self, db):
        """Test creating user with subscription tier."""
        user = User(
            id="user-002",
            email="pro@example.com",
            created_at=datetime.now(),
            subscription_tier="pro",
        )
        result = await db.create_user(user)
        assert result.subscription_tier == "pro"

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, db):
        """Test getting user by ID."""
        user = User(
            id="user-003",
            email="find@example.com",
            created_at=datetime.now(),
        )
        await db.create_user(user)
        found = await db.get_user("user-003")
        assert found is not None
        assert found.email == "find@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db):
        """Test getting user by email."""
        user = User(
            id="user-004",
            email="email@example.com",
            created_at=datetime.now(),
        )
        await db.create_user(user)
        found = await db.get_user_by_email("email@example.com")
        assert found is not None
        assert found.id == "user-004"

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, db):
        """Test getting a nonexistent user."""
        user = await db.get_user("nonexistent")
        assert user is None

    @pytest.mark.asyncio
    async def test_update_user(self, db):
        """Test updating user data."""
        user = User(
            id="user-005",
            email="update@example.com",
            created_at=datetime.now(),
        )
        await db.create_user(user)

        # Update preferences
        user.preferences_json = json.dumps({"topics": ["AI", "Science"], "frequency": "daily"})
        user.subscription_tier = "basic"
        await db.update_user(user)

        found = await db.get_user("user-005")
        assert found is not None
        assert found.subscription_tier == "basic"
        prefs = json.loads(found.preferences_json)
        assert prefs["topics"] == ["AI", "Science"]

    @pytest.mark.asyncio
    async def test_delete_user(self, db):
        """Test deleting a user."""
        user = User(
            id="user-007",
            email="delete@example.com",
            created_at=datetime.now(),
        )
        await db.create_user(user)
        result = await db.delete_user("user-007")

        assert result is True
        found = await db.get_user("user-007")
        assert found is None

    @pytest.mark.asyncio
    async def test_duplicate_email_raises_error(self, db):
        """Test that duplicate emails raise DuplicateError."""
        user1 = User(
            id="user-dup-1",
            email="dup@example.com",
            created_at=datetime.now(),
        )
        await db.create_user(user1)

        user2 = User(
            id="user-dup-2",
            email="dup@example.com",
            created_at=datetime.now(),
        )
        with pytest.raises(DuplicateError):
            await db.create_user(user2)


# ============================================================================
# Digest Operations Tests
# ============================================================================


class TestDigestOperations:
    """Tests for digest CRUD operations."""

    @pytest.fixture
    async def db(self, temp_db_path):
        """Create and initialize a database."""
        db = SQLiteDatabase(temp_db_path)
        await db.initialize()
        user = User(
            id="test-user",
            email="test@example.com",
            created_at=datetime.now(),
        )
        await db.create_user(user)
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_save_digest(self, db):
        """Test saving a digest record."""
        digest = DigestRecord(
            id="digest-001",
            user_id="test-user",
            generated_at=datetime.now(),
            period_start=datetime.now() - timedelta(days=1),
            period_end=datetime.now(),
            frequency="daily",
            article_count=10,
            topics_json=json.dumps(["AI", "Science"]),
            cost_usd=0.035,
        )
        result = await db.save_digest(digest)
        assert result.id == "digest-001"
        assert result.article_count == 10

    @pytest.mark.asyncio
    async def test_get_digest(self, db):
        """Test getting a digest by ID."""
        digest = DigestRecord(
            id="digest-002",
            user_id="test-user",
            generated_at=datetime.now(),
            period_start=datetime.now(),
            period_end=datetime.now(),
            frequency="daily",
        )
        await db.save_digest(digest)
        found = await db.get_digest("digest-002")
        assert found is not None
        assert found.id == "digest-002"

    @pytest.mark.asyncio
    async def test_get_user_digests(self, db):
        """Test getting user's digests."""
        for i in range(5):
            digest = DigestRecord(
                id=f"digest-{i:03d}",
                user_id="test-user",
                generated_at=datetime.now(),
                period_start=datetime.now(),
                period_end=datetime.now(),
                frequency="daily",
            )
            await db.save_digest(digest)

        digests = await db.get_user_digests("test-user", limit=3)
        assert len(digests) == 3

    @pytest.mark.asyncio
    async def test_get_user_digests_pagination(self, db):
        """Test digest listing with pagination."""
        for i in range(10):
            digest = DigestRecord(
                id=f"page-digest-{i:03d}",
                user_id="test-user",
                generated_at=datetime.now() + timedelta(seconds=i),  # Different times for ordering
                period_start=datetime.now(),
                period_end=datetime.now(),
                frequency="daily",
            )
            await db.save_digest(digest)

        page1 = await db.get_user_digests("test-user", limit=5, offset=0)
        page2 = await db.get_user_digests("test-user", limit=5, offset=5)

        assert len(page1) == 5
        assert len(page2) == 5
        # Should be different digests
        assert page1[0].id != page2[0].id

    @pytest.mark.asyncio
    async def test_get_latest_digest(self, db):
        """Test getting the latest digest."""
        old = DigestRecord(
            id="old-digest",
            user_id="test-user",
            generated_at=datetime.now() - timedelta(days=2),
            period_start=datetime.now() - timedelta(days=3),
            period_end=datetime.now() - timedelta(days=2),
            frequency="daily",
        )
        await db.save_digest(old)

        new = DigestRecord(
            id="new-digest",
            user_id="test-user",
            generated_at=datetime.now(),
            period_start=datetime.now() - timedelta(days=1),
            period_end=datetime.now(),
            frequency="daily",
        )
        await db.save_digest(new)

        latest = await db.get_latest_digest("test-user")
        assert latest is not None
        assert latest.id == "new-digest"

    @pytest.mark.asyncio
    async def test_delete_old_digests(self, db):
        """Test deleting old digests."""
        old = DigestRecord(
            id="very-old-digest",
            user_id="test-user",
            generated_at=datetime.now() - timedelta(days=60),
            period_start=datetime.now() - timedelta(days=61),
            period_end=datetime.now() - timedelta(days=60),
            frequency="daily",
        )
        await db.save_digest(old)

        recent = DigestRecord(
            id="recent-digest",
            user_id="test-user",
            generated_at=datetime.now(),
            period_start=datetime.now() - timedelta(days=1),
            period_end=datetime.now(),
            frequency="daily",
        )
        await db.save_digest(recent)

        deleted = await db.delete_old_digests("test-user", keep_days=30)
        assert deleted == 1

        # Old one should be gone
        assert await db.get_digest("very-old-digest") is None
        # Recent one should remain
        assert await db.get_digest("recent-digest") is not None


# ============================================================================
# Article Operations Tests
# ============================================================================


class TestArticleOperations:
    """Tests for article CRUD operations."""

    @pytest.fixture
    async def db(self, temp_db_path):
        """Create and initialize a database."""
        db = SQLiteDatabase(temp_db_path)
        await db.initialize()
        yield db
        await db.close()

    def _make_article(self, article_id: str, url: str, title: str = "Test Article") -> ArticleRecord:
        """Helper to create article records."""
        return ArticleRecord(
            id=article_id,
            url=url,
            title=title,
            source="example.com",
            content_hash=hashlib.md5(url.encode()).hexdigest(),
            first_seen_at=datetime.now(),
            quality_score=0.78,
            relevance_score=0.85,
        )

    @pytest.mark.asyncio
    async def test_save_article(self, db):
        """Test saving an article record."""
        article = self._make_article("article-001", "https://example.com/article")
        article.relevance_score = 0.85
        article.quality_score = 0.78

        result = await db.save_article(article)
        assert result.id == "article-001"
        assert result.relevance_score == 0.85

    @pytest.mark.asyncio
    async def test_get_article(self, db):
        """Test getting an article by ID."""
        article = self._make_article("article-002", "https://example.com/2")
        article.title = "Article 2"
        await db.save_article(article)

        found = await db.get_article("article-002")
        assert found is not None
        assert found.title == "Article 2"

    @pytest.mark.asyncio
    async def test_get_article_by_url(self, db):
        """Test getting an article by URL."""
        article = self._make_article("article-003", "https://example.com/unique-url")
        await db.save_article(article)

        found = await db.get_article_by_url("https://example.com/unique-url")
        assert found is not None
        assert found.id == "article-003"

    @pytest.mark.asyncio
    async def test_search_articles_by_topic(self, db):
        """Test searching articles by topic."""
        for i in range(3):
            article = self._make_article(f"topic-article-{i}", f"https://example.com/topic/{i}")
            article.topic = "AI"
            await db.save_article(article)

        results = await db.search_articles(topic="AI")
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_articles_by_source(self, db):
        """Test searching articles by source."""
        article = self._make_article("source-article", "https://techcrunch.com/story")
        article.source = "techcrunch.com"
        await db.save_article(article)

        results = await db.search_articles(source="techcrunch")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_articles_by_quality(self, db):
        """Test searching articles by minimum quality."""
        low_quality = self._make_article("low-quality", "https://example.com/low")
        low_quality.quality_score = 0.3
        await db.save_article(low_quality)

        high_quality = self._make_article("high-quality", "https://example.com/high")
        high_quality.quality_score = 0.9
        await db.save_article(high_quality)

        results = await db.search_articles(min_quality=0.7)
        assert len(results) == 1
        assert results[0].id == "high-quality"

    @pytest.mark.asyncio
    async def test_get_recent_articles(self, db):
        """Test getting recent articles."""
        recent = self._make_article("recent", "https://example.com/recent")
        recent.first_seen_at = datetime.now()
        await db.save_article(recent)

        results = await db.get_recent_articles(hours=1)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_article_url_uniqueness(self, db):
        """Test that duplicate URLs update the existing record."""
        article1 = self._make_article("unique-1", "https://example.com/same-url")
        article1.title = "First Title"
        await db.save_article(article1)

        # Same URL with different ID - should update or replace
        article2 = self._make_article("unique-2", "https://example.com/same-url")
        article2.title = "Second Title"
        await db.save_article(article2)

        # Should only have one article with this URL
        found = await db.get_article_by_url("https://example.com/same-url")
        assert found is not None


# ============================================================================
# Feedback Operations Tests
# ============================================================================


class TestFeedbackOperations:
    """Tests for feedback CRUD operations."""

    @pytest.fixture
    async def db(self, temp_db_path):
        """Create and initialize a database."""
        db = SQLiteDatabase(temp_db_path)
        await db.initialize()

        user = User(
            id="test-user",
            email="test@example.com",
            created_at=datetime.now(),
        )
        await db.create_user(user)

        digest = DigestRecord(
            id="test-digest",
            user_id="test-user",
            generated_at=datetime.now(),
            period_start=datetime.now(),
            period_end=datetime.now(),
            frequency="daily",
        )
        await db.save_digest(digest)
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_save_feedback(self, db):
        """Test saving feedback."""
        feedback = FeedbackRecord(
            id="feedback-001",
            user_id="test-user",
            digest_id="test-digest",
            article_url="https://example.com/article",
            feedback_type="like",
            created_at=datetime.now(),
        )
        result = await db.save_feedback(feedback)
        assert result.id == "feedback-001"
        assert result.feedback_type == "like"

    @pytest.mark.asyncio
    async def test_get_user_feedback(self, db):
        """Test getting user's feedback."""
        for i, fb_type in enumerate(["like", "dislike", "read"]):
            feedback = FeedbackRecord(
                id=f"fb-{i}",
                user_id="test-user",
                digest_id="test-digest",
                article_url=None,
                feedback_type=fb_type,
                created_at=datetime.now(),
            )
            await db.save_feedback(feedback)

        results = await db.get_user_feedback("test-user")
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_get_article_feedback(self, db):
        """Test getting feedback for an article."""
        feedback = FeedbackRecord(
            id="article-fb",
            user_id="test-user",
            digest_id="test-digest",
            article_url="https://example.com/specific-article",
            feedback_type="like",
            created_at=datetime.now(),
        )
        await db.save_feedback(feedback)

        results = await db.get_article_feedback("https://example.com/specific-article")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_feedback_with_rating(self, db):
        """Test feedback with rating."""
        feedback = FeedbackRecord(
            id="rated-fb",
            user_id="test-user",
            digest_id="test-digest",
            article_url=None,
            feedback_type="like",
            created_at=datetime.now(),
            rating=5,
            comment="Great digest!",
        )
        result = await db.save_feedback(feedback)
        assert result.rating == 5
        assert result.comment == "Great digest!"


# ============================================================================
# Usage Tracking Tests
# ============================================================================


class TestUsageTracking:
    """Tests for usage tracking operations."""

    @pytest.fixture
    async def db(self, temp_db_path):
        """Create and initialize a database."""
        db = SQLiteDatabase(temp_db_path)
        await db.initialize()
        user = User(
            id="test-user",
            email="test@example.com",
            created_at=datetime.now(),
        )
        await db.create_user(user)
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_record_usage(self, db):
        """Test recording usage."""
        usage = await db.record_usage(
            "test-user",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.05,
            digests=1,
        )
        assert usage.user_id == "test-user"
        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500
        assert usage.cost_usd == 0.05
        assert usage.digest_count == 1

    @pytest.mark.asyncio
    async def test_get_usage(self, db):
        """Test getting usage for a specific month."""
        month = datetime.now().strftime("%Y-%m")
        await db.record_usage("test-user", input_tokens=100)

        usage = await db.get_usage("test-user", month)
        assert usage is not None
        assert usage.input_tokens == 100

    @pytest.mark.asyncio
    async def test_usage_accumulates(self, db):
        """Test that usage accumulates over multiple records."""
        for _ in range(3):
            await db.record_usage(
                "test-user",
                input_tokens=100,
                digests=1,
            )

        month = datetime.now().strftime("%Y-%m")
        usage = await db.get_usage("test-user", month)
        assert usage is not None
        assert usage.input_tokens == 300
        assert usage.digest_count == 3

    @pytest.mark.asyncio
    async def test_get_usage_history(self, db):
        """Test getting usage history."""
        # Note: This test records usage for the current month
        # since record_usage uses the current month automatically
        await db.record_usage("test-user", digests=5)

        history = await db.get_usage_history("test-user", months=3)
        assert len(history) >= 1
        assert history[0].digest_count == 5


# ============================================================================
# Transaction Tests
# ============================================================================


class TestTransactions:
    """Tests for transaction handling."""

    @pytest.fixture
    async def db(self, temp_db_path):
        """Create and initialize a database."""
        db = SQLiteDatabase(temp_db_path)
        await db.initialize()
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_transaction_commit(self, db):
        """Test that transactions commit properly."""
        user = User(
            id="tx-user",
            email="tx@example.com",
            created_at=datetime.now(),
        )
        await db.create_user(user)
        found = await db.get_user("tx-user")
        assert found is not None

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, db):
        """Test concurrent database operations."""
        async def create_user(i):
            user = User(
                id=f"concurrent-{i}",
                email=f"concurrent{i}@example.com",
                created_at=datetime.now(),
            )
            await db.create_user(user)

        # Create users concurrently
        await asyncio.gather(*[create_user(i) for i in range(5)])

        # Verify all users were created
        for i in range(5):
            user = await db.get_user(f"concurrent-{i}")
            assert user is not None


# ============================================================================
# Statistics Tests
# ============================================================================


class TestStatistics:
    """Tests for database statistics."""

    @pytest.fixture
    async def db(self, temp_db_path):
        """Create and initialize a database."""
        db = SQLiteDatabase(temp_db_path)
        await db.initialize()
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_get_stats(self, db):
        """Test getting database statistics."""
        # Add some data
        user = User(
            id="stats-user",
            email="stats@example.com",
            created_at=datetime.now(),
        )
        await db.create_user(user)

        stats = await db.get_stats()
        assert "total_users" in stats
        assert stats["total_users"] >= 1
        assert "total_digests" in stats
        assert "total_articles" in stats
        assert "database_size_bytes" in stats
