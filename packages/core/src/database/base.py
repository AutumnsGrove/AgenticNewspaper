"""Base database interface and common types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DatabaseType(Enum):
    """Supported database types."""

    SQLITE = "sqlite"
    D1 = "d1"
    MEMORY = "memory"  # For testing


class DatabaseError(Exception):
    """Base database exception."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


class NotFoundError(DatabaseError):
    """Resource not found."""

    pass


class DuplicateError(DatabaseError):
    """Duplicate resource."""

    pass


class ConnectionError(DatabaseError):
    """Database connection error."""

    pass


@dataclass
class User:
    """User account."""

    id: str
    email: str
    created_at: datetime
    subscription_tier: str = "free"
    preferences_json: str = "{}"
    last_digest_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "subscription_tier": self.subscription_tier,
            "last_digest_at": self.last_digest_at.isoformat() if self.last_digest_at else None,
        }


@dataclass
class DigestRecord:
    """Stored digest record."""

    id: str
    user_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    frequency: str
    r2_key: str | None = None  # For cloud storage
    markdown: str = ""  # For local storage
    article_count: int = 0
    topics_json: str = "[]"
    cost_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "generated_at": self.generated_at.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "frequency": self.frequency,
            "r2_key": self.r2_key,
            "article_count": self.article_count,
            "cost_usd": self.cost_usd,
        }


@dataclass
class ArticleRecord:
    """Stored article record."""

    id: str
    url: str
    title: str
    source: str
    content_hash: str
    first_seen_at: datetime
    topic: str | None = None
    author: str | None = None
    published_date: datetime | None = None
    word_count: int = 0
    quality_score: float | None = None
    relevance_score: float | None = None
    bias_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "source": self.source,
            "content_hash": self.content_hash,
            "first_seen_at": self.first_seen_at.isoformat(),
            "topic": self.topic,
            "author": self.author,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "word_count": self.word_count,
            "quality_score": self.quality_score,
            "relevance_score": self.relevance_score,
            "bias_score": self.bias_score,
        }


@dataclass
class FeedbackRecord:
    """User feedback on articles/digests."""

    id: str
    user_id: str
    digest_id: str
    article_url: str | None
    feedback_type: str  # 'like', 'dislike', 'read', 'skip'
    created_at: datetime
    rating: int | None = None  # 1-5 star rating
    comment: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "digest_id": self.digest_id,
            "article_url": self.article_url,
            "feedback_type": self.feedback_type,
            "created_at": self.created_at.isoformat(),
            "rating": self.rating,
            "comment": self.comment,
        }


@dataclass
class UsageRecord:
    """Monthly usage tracking."""

    id: str
    user_id: str
    month: str  # 'YYYY-MM'
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    digest_count: int = 0
    search_count: int = 0
    articles_analyzed: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "month": self.month,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "digest_count": self.digest_count,
            "search_count": self.search_count,
            "articles_analyzed": self.articles_analyzed,
        }


class DatabaseInterface(ABC):
    """Abstract base class for database implementations."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize database schema."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close database connection."""
        pass

    # User operations
    @abstractmethod
    async def create_user(self, user: User) -> User:
        """Create a new user."""
        pass

    @abstractmethod
    async def get_user(self, user_id: str) -> User | None:
        """Get user by ID."""
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        pass

    @abstractmethod
    async def update_user(self, user: User) -> User:
        """Update user data."""
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete user and all associated data."""
        pass

    # Digest operations
    @abstractmethod
    async def save_digest(self, digest: DigestRecord) -> DigestRecord:
        """Save a digest record."""
        pass

    @abstractmethod
    async def get_digest(self, digest_id: str) -> DigestRecord | None:
        """Get digest by ID."""
        pass

    @abstractmethod
    async def get_user_digests(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> list[DigestRecord]:
        """Get user's digests, ordered by date descending."""
        pass

    @abstractmethod
    async def get_latest_digest(self, user_id: str) -> DigestRecord | None:
        """Get user's most recent digest."""
        pass

    @abstractmethod
    async def delete_old_digests(self, user_id: str, keep_days: int = 30) -> int:
        """Delete digests older than keep_days. Returns count deleted."""
        pass

    # Article operations
    @abstractmethod
    async def save_article(self, article: ArticleRecord) -> ArticleRecord:
        """Save an article record. Updates if URL exists."""
        pass

    @abstractmethod
    async def get_article(self, article_id: str) -> ArticleRecord | None:
        """Get article by ID."""
        pass

    @abstractmethod
    async def get_article_by_url(self, url: str) -> ArticleRecord | None:
        """Get article by URL."""
        pass

    @abstractmethod
    async def search_articles(
        self,
        query: str | None = None,
        topic: str | None = None,
        source: str | None = None,
        min_quality: float | None = None,
        limit: int = 50,
    ) -> list[ArticleRecord]:
        """Search articles with filters."""
        pass

    @abstractmethod
    async def get_recent_articles(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> list[ArticleRecord]:
        """Get recently seen articles."""
        pass

    # Feedback operations
    @abstractmethod
    async def save_feedback(self, feedback: FeedbackRecord) -> FeedbackRecord:
        """Save user feedback."""
        pass

    @abstractmethod
    async def get_user_feedback(
        self,
        user_id: str,
        limit: int = 100,
    ) -> list[FeedbackRecord]:
        """Get user's feedback history."""
        pass

    @abstractmethod
    async def get_article_feedback(
        self,
        article_url: str,
    ) -> list[FeedbackRecord]:
        """Get all feedback for an article."""
        pass

    # Usage tracking
    @abstractmethod
    async def record_usage(
        self,
        user_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        digests: int = 0,
        searches: int = 0,
        articles: int = 0,
    ) -> UsageRecord:
        """Record usage for current month."""
        pass

    @abstractmethod
    async def get_usage(self, user_id: str, month: str) -> UsageRecord | None:
        """Get usage for a specific month."""
        pass

    @abstractmethod
    async def get_usage_history(
        self,
        user_id: str,
        months: int = 6,
    ) -> list[UsageRecord]:
        """Get usage history for past N months."""
        pass

    # Statistics
    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        pass

    # Context manager
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
