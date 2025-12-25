"""
Tests for the SQLite database implementation.
"""

import pytest
from datetime import datetime, timedelta
import json
import asyncio

from src.database.sqlite import SQLiteDatabase
from src.database.base import User, DigestRecord, ArticleRecord, FeedbackRecord, UsageRecord


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
        async with db._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = await cursor.fetchall()
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

        async with db._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
            indexes = await cursor.fetchall()

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
        user = await db.create_user(
            user_id="user-001",
            email="test@example.com",
            preferences={"topics": ["AI"]},
        )
        assert user.id == "user-001"
        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_create_user_with_tier(self, db):
        """Test creating user with subscription tier."""
        user = await db.create_user(
            user_id="user-002",
            email="pro@example.com",
            subscription_tier="pro",
        )
        assert user.subscription_tier == "pro"

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, db):
        """Test getting user by ID."""
        await db.create_user(user_id="user-003", email="find@example.com")
        user = await db.get_user("user-003")
        assert user is not None
        assert user.email == "find@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db):
        """Test getting user by email."""
        await db.create_user(user_id="user-004", email="email@example.com")
        user = await db.get_user_by_email("email@example.com")
        assert user is not None
        assert user.id == "user-004"

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, db):
        """Test getting a nonexistent user."""
        user = await db.get_user("nonexistent")
        assert user is None

    @pytest.mark.asyncio
    async def test_update_user_preferences(self, db):
        """Test updating user preferences."""
        await db.create_user(user_id="user-005", email="update@example.com")
        new_prefs = {"topics": ["AI", "Science"], "frequency": "daily"}
        await db.update_user_preferences("user-005", new_prefs)

        user = await db.get_user("user-005")
        assert user.preferences == new_prefs

    @pytest.mark.asyncio
    async def test_update_user_tier(self, db):
        """Test updating user subscription tier."""
        await db.create_user(user_id="user-006", email="tier@example.com")
        await db.update_user_tier("user-006", "basic")

        user = await db.get_user("user-006")
        assert user.subscription_tier == "basic"

    @pytest.mark.asyncio
    async def test_delete_user(self, db):
        """Test deleting a user."""
        await db.create_user(user_id="user-007", email="delete@example.com")
        await db.delete_user("user-007")

        user = await db.get_user("user-007")
        assert user is None


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
        await db.create_user(user_id="test-user", email="test@example.com")
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_create_digest(self, db):
        """Test creating a digest record."""
        digest = await db.create_digest(
            digest_id="digest-001",
            user_id="test-user",
            period_start=datetime.now() - timedelta(days=1),
            period_end=datetime.now(),
            frequency="daily",
            content={"sections": []},
            article_count=10,
            topics=["AI", "Science"],
            cost_usd=0.035,
        )
        assert digest.id == "digest-001"
        assert digest.article_count == 10

    @pytest.mark.asyncio
    async def test_get_digest(self, db):
        """Test getting a digest by ID."""
        await db.create_digest(
            digest_id="digest-002",
            user_id="test-user",
            period_start=datetime.now(),
            period_end=datetime.now(),
            frequency="daily",
            content={},
        )
        digest = await db.get_digest("digest-002")
        assert digest is not None

    @pytest.mark.asyncio
    async def test_list_user_digests(self, db):
        """Test listing user's digests."""
        for i in range(5):
            await db.create_digest(
                digest_id=f"digest-{i:03d}",
                user_id="test-user",
                period_start=datetime.now(),
                period_end=datetime.now(),
                frequency="daily",
                content={},
            )

        digests = await db.list_user_digests("test-user", limit=3)
        assert len(digests) == 3

    @pytest.mark.asyncio
    async def test_list_digests_pagination(self, db):
        """Test digest listing with pagination."""
        for i in range(10):
            await db.create_digest(
                digest_id=f"page-digest-{i:03d}",
                user_id="test-user",
                period_start=datetime.now(),
                period_end=datetime.now(),
                frequency="daily",
                content={},
            )

        page1 = await db.list_user_digests("test-user", limit=5, offset=0)
        page2 = await db.list_user_digests("test-user", limit=5, offset=5)

        assert len(page1) == 5
        assert len(page2) == 5
        # Should be different digests
        assert page1[0].id != page2[0].id

    @pytest.mark.asyncio
    async def test_get_latest_digest(self, db):
        """Test getting the latest digest."""
        await db.create_digest(
            digest_id="old-digest",
            user_id="test-user",
            period_start=datetime.now() - timedelta(days=2),
            period_end=datetime.now() - timedelta(days=1),
            frequency="daily",
            content={},
        )
        await db.create_digest(
            digest_id="new-digest",
            user_id="test-user",
            period_start=datetime.now() - timedelta(days=1),
            period_end=datetime.now(),
            frequency="daily",
            content={},
        )

        latest = await db.get_latest_digest("test-user")
        assert latest is not None
        assert latest.id == "new-digest"


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
        await db.create_user(user_id="test-user", email="test@example.com")
        await db.create_digest(
            digest_id="test-digest",
            user_id="test-user",
            period_start=datetime.now(),
            period_end=datetime.now(),
            frequency="daily",
            content={},
        )
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_create_article(self, db):
        """Test creating an article record."""
        article = await db.create_article(
            article_id="article-001",
            digest_id="test-digest",
            url="https://example.com/article",
            title="Test Article",
            source="example.com",
            content="Article content...",
            summary="Brief summary",
            relevance_score=0.85,
            quality_score=0.78,
        )
        assert article.id == "article-001"
        assert article.relevance_score == 0.85

    @pytest.mark.asyncio
    async def test_get_article(self, db):
        """Test getting an article by ID."""
        await db.create_article(
            article_id="article-002",
            digest_id="test-digest",
            url="https://example.com/2",
            title="Article 2",
            source="example.com",
        )
        article = await db.get_article("article-002")
        assert article is not None
        assert article.title == "Article 2"

    @pytest.mark.asyncio
    async def test_get_articles_by_digest(self, db):
        """Test getting articles by digest ID."""
        for i in range(3):
            await db.create_article(
                article_id=f"digest-article-{i}",
                digest_id="test-digest",
                url=f"https://example.com/{i}",
                title=f"Article {i}",
                source="example.com",
            )

        articles = await db.get_articles_by_digest("test-digest")
        assert len(articles) == 3

    @pytest.mark.asyncio
    async def test_article_url_deduplication(self, db):
        """Test that duplicate URLs are handled."""
        await db.create_article(
            article_id="unique-1",
            digest_id="test-digest",
            url="https://example.com/same-url",
            title="First Article",
            source="example.com",
        )

        # Second article with same URL should update or be rejected
        # depending on implementation
        try:
            await db.create_article(
                article_id="unique-2",
                digest_id="test-digest",
                url="https://example.com/same-url",
                title="Second Article",
                source="example.com",
            )
        except Exception:
            pass  # Expected behavior

        articles = await db.get_articles_by_url("https://example.com/same-url")
        assert len(articles) >= 1


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
        await db.create_user(user_id="test-user", email="test@example.com")
        await db.create_digest(
            digest_id="test-digest",
            user_id="test-user",
            period_start=datetime.now(),
            period_end=datetime.now(),
            frequency="daily",
            content={},
        )
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_create_feedback(self, db):
        """Test creating feedback."""
        feedback = await db.create_feedback(
            feedback_id="feedback-001",
            user_id="test-user",
            digest_id="test-digest",
            feedback_type="like",
            article_url="https://example.com/article",
        )
        assert feedback.id == "feedback-001"
        assert feedback.type == "like"

    @pytest.mark.asyncio
    async def test_get_user_feedback(self, db):
        """Test getting user's feedback."""
        for i, fb_type in enumerate(["like", "dislike", "read"]):
            await db.create_feedback(
                feedback_id=f"fb-{i}",
                user_id="test-user",
                digest_id="test-digest",
                feedback_type=fb_type,
            )

        feedback = await db.get_user_feedback("test-user")
        assert len(feedback) == 3

    @pytest.mark.asyncio
    async def test_get_digest_feedback(self, db):
        """Test getting feedback for a digest."""
        await db.create_feedback(
            feedback_id="digest-fb",
            user_id="test-user",
            digest_id="test-digest",
            feedback_type="like",
        )

        feedback = await db.get_digest_feedback("test-digest")
        assert len(feedback) == 1


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
        await db.create_user(user_id="test-user", email="test@example.com")
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_get_or_create_usage(self, db):
        """Test getting or creating usage record."""
        usage = await db.get_or_create_usage("test-user", "2025-12")
        assert usage.user_id == "test-user"
        assert usage.month == "2025-12"
        assert usage.digest_count == 0

    @pytest.mark.asyncio
    async def test_increment_usage(self, db):
        """Test incrementing usage counters."""
        await db.get_or_create_usage("test-user", "2025-12")
        await db.increment_usage(
            "test-user",
            "2025-12",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.05,
            digest_count=1,
        )

        usage = await db.get_or_create_usage("test-user", "2025-12")
        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500
        assert usage.cost_usd == 0.05
        assert usage.digest_count == 1

    @pytest.mark.asyncio
    async def test_usage_accumulates(self, db):
        """Test that usage accumulates over multiple increments."""
        await db.get_or_create_usage("test-user", "2025-12")

        for _ in range(3):
            await db.increment_usage(
                "test-user",
                "2025-12",
                input_tokens=100,
                digest_count=1,
            )

        usage = await db.get_or_create_usage("test-user", "2025-12")
        assert usage.input_tokens == 300
        assert usage.digest_count == 3

    @pytest.mark.asyncio
    async def test_get_usage_history(self, db):
        """Test getting usage history."""
        for month in ["2025-10", "2025-11", "2025-12"]:
            await db.get_or_create_usage("test-user", month)
            await db.increment_usage("test-user", month, digest_count=1)

        history = await db.get_usage_history("test-user", months=3)
        assert len(history) == 3


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
        await db.create_user(user_id="tx-user", email="tx@example.com")
        user = await db.get_user("tx-user")
        assert user is not None

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, db):
        """Test concurrent database operations."""
        async def create_user(i):
            await db.create_user(
                user_id=f"concurrent-{i}",
                email=f"concurrent{i}@example.com"
            )

        # Create users concurrently
        await asyncio.gather(*[create_user(i) for i in range(5)])

        # Verify all users were created
        for i in range(5):
            user = await db.get_user(f"concurrent-{i}")
            assert user is not None
