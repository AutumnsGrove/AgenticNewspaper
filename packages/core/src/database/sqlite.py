"""SQLite database implementation for local development and self-hosted deployments."""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

from .base import (
    DatabaseInterface,
    DatabaseError,
    NotFoundError,
    DuplicateError,
    User,
    DigestRecord,
    ArticleRecord,
    FeedbackRecord,
    UsageRecord,
)


# SQL Schema
SCHEMA_SQL = """
-- Users
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL,
    subscription_tier TEXT DEFAULT 'free',
    preferences_json TEXT DEFAULT '{}',
    last_digest_at TEXT
);

-- Digests
CREATE TABLE IF NOT EXISTS digests (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    frequency TEXT NOT NULL,
    r2_key TEXT,
    markdown TEXT,
    article_count INTEGER DEFAULT 0,
    topics_json TEXT DEFAULT '[]',
    cost_usd REAL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Articles
CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    topic TEXT,
    author TEXT,
    published_date TEXT,
    word_count INTEGER DEFAULT 0,
    quality_score REAL,
    relevance_score REAL,
    bias_score REAL
);

-- Feedback
CREATE TABLE IF NOT EXISTS feedback (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    digest_id TEXT NOT NULL,
    article_url TEXT,
    feedback_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    rating INTEGER,
    comment TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (digest_id) REFERENCES digests(id) ON DELETE CASCADE
);

-- Usage tracking
CREATE TABLE IF NOT EXISTS usage (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    month TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    digest_count INTEGER DEFAULT 0,
    search_count INTEGER DEFAULT 0,
    articles_analyzed INTEGER DEFAULT 0,
    UNIQUE(user_id, month),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_digests_user ON digests(user_id, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_topic ON articles(topic);
CREATE INDEX IF NOT EXISTS idx_articles_first_seen ON articles(first_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_user_month ON usage(user_id, month);
"""


class SQLiteDatabase(DatabaseInterface):
    """SQLite database implementation using aiosqlite."""

    def __init__(self, db_path: str = "data/clearing.db"):
        """
        Initialize SQLite database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None
        self._initialized = False

    async def _get_db(self) -> aiosqlite.Connection:
        """Get database connection, creating if needed."""
        if self._db is None:
            # Ensure directory exists
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

            self._db = await aiosqlite.connect(self.db_path)
            self._db.row_factory = aiosqlite.Row

            # Enable foreign keys
            await self._db.execute("PRAGMA foreign_keys = ON")

        return self._db

    async def initialize(self) -> None:
        """Initialize database schema."""
        if self._initialized:
            return

        db = await self._get_db()
        await db.executescript(SCHEMA_SQL)
        await db.commit()
        self._initialized = True

    async def close(self) -> None:
        """Close database connection."""
        if self._db:
            await self._db.close()
            self._db = None
            self._initialized = False

    def _parse_datetime(self, value: str | None) -> datetime | None:
        """Parse ISO datetime string."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    # User operations
    async def create_user(self, user: User) -> User:
        """Create a new user."""
        db = await self._get_db()

        try:
            await db.execute(
                """
                INSERT INTO users (id, email, created_at, subscription_tier, preferences_json, last_digest_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user.id,
                    user.email,
                    user.created_at.isoformat(),
                    user.subscription_tier,
                    user.preferences_json,
                    user.last_digest_at.isoformat() if user.last_digest_at else None,
                ),
            )
            await db.commit()
            return user
        except aiosqlite.IntegrityError as e:
            if "UNIQUE constraint" in str(e):
                raise DuplicateError(f"User with email {user.email} already exists")
            raise DatabaseError(f"Failed to create user: {e}")

    async def get_user(self, user_id: str) -> User | None:
        """Get user by ID."""
        db = await self._get_db()
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        await cursor.close()

        if not row:
            return None

        return User(
            id=row["id"],
            email=row["email"],
            created_at=datetime.fromisoformat(row["created_at"]),
            subscription_tier=row["subscription_tier"],
            preferences_json=row["preferences_json"],
            last_digest_at=self._parse_datetime(row["last_digest_at"]),
        )

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        db = await self._get_db()
        cursor = await db.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = await cursor.fetchone()
        await cursor.close()

        if not row:
            return None

        return User(
            id=row["id"],
            email=row["email"],
            created_at=datetime.fromisoformat(row["created_at"]),
            subscription_tier=row["subscription_tier"],
            preferences_json=row["preferences_json"],
            last_digest_at=self._parse_datetime(row["last_digest_at"]),
        )

    async def update_user(self, user: User) -> User:
        """Update user data."""
        db = await self._get_db()

        await db.execute(
            """
            UPDATE users
            SET email = ?, subscription_tier = ?, preferences_json = ?, last_digest_at = ?
            WHERE id = ?
            """,
            (
                user.email,
                user.subscription_tier,
                user.preferences_json,
                user.last_digest_at.isoformat() if user.last_digest_at else None,
                user.id,
            ),
        )
        await db.commit()
        return user

    async def delete_user(self, user_id: str) -> bool:
        """Delete user and all associated data."""
        db = await self._get_db()
        cursor = await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await db.commit()
        deleted = cursor.rowcount > 0
        await cursor.close()
        return deleted

    # Digest operations
    async def save_digest(self, digest: DigestRecord) -> DigestRecord:
        """Save a digest record."""
        db = await self._get_db()

        await db.execute(
            """
            INSERT OR REPLACE INTO digests
            (id, user_id, generated_at, period_start, period_end, frequency, r2_key, markdown, article_count, topics_json, cost_usd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                digest.id,
                digest.user_id,
                digest.generated_at.isoformat(),
                digest.period_start.isoformat(),
                digest.period_end.isoformat(),
                digest.frequency,
                digest.r2_key,
                digest.markdown,
                digest.article_count,
                digest.topics_json,
                digest.cost_usd,
            ),
        )
        await db.commit()
        return digest

    async def get_digest(self, digest_id: str) -> DigestRecord | None:
        """Get digest by ID."""
        db = await self._get_db()
        cursor = await db.execute("SELECT * FROM digests WHERE id = ?", (digest_id,))
        row = await cursor.fetchone()
        await cursor.close()

        if not row:
            return None

        return DigestRecord(
            id=row["id"],
            user_id=row["user_id"],
            generated_at=datetime.fromisoformat(row["generated_at"]),
            period_start=datetime.fromisoformat(row["period_start"]),
            period_end=datetime.fromisoformat(row["period_end"]),
            frequency=row["frequency"],
            r2_key=row["r2_key"],
            markdown=row["markdown"] or "",
            article_count=row["article_count"],
            topics_json=row["topics_json"],
            cost_usd=row["cost_usd"],
        )

    async def get_user_digests(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> list[DigestRecord]:
        """Get user's digests, ordered by date descending."""
        db = await self._get_db()
        cursor = await db.execute(
            """
            SELECT * FROM digests
            WHERE user_id = ?
            ORDER BY generated_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        )
        rows = await cursor.fetchall()
        await cursor.close()

        return [
            DigestRecord(
                id=row["id"],
                user_id=row["user_id"],
                generated_at=datetime.fromisoformat(row["generated_at"]),
                period_start=datetime.fromisoformat(row["period_start"]),
                period_end=datetime.fromisoformat(row["period_end"]),
                frequency=row["frequency"],
                r2_key=row["r2_key"],
                markdown=row["markdown"] or "",
                article_count=row["article_count"],
                topics_json=row["topics_json"],
                cost_usd=row["cost_usd"],
            )
            for row in rows
        ]

    async def get_latest_digest(self, user_id: str) -> DigestRecord | None:
        """Get user's most recent digest."""
        digests = await self.get_user_digests(user_id, limit=1)
        return digests[0] if digests else None

    async def delete_old_digests(self, user_id: str, keep_days: int = 30) -> int:
        """Delete digests older than keep_days."""
        db = await self._get_db()
        cutoff = (datetime.now() - timedelta(days=keep_days)).isoformat()

        cursor = await db.execute(
            """
            DELETE FROM digests
            WHERE user_id = ? AND generated_at < ?
            """,
            (user_id, cutoff),
        )
        await db.commit()
        deleted = cursor.rowcount
        await cursor.close()
        return deleted

    # Article operations
    async def save_article(self, article: ArticleRecord) -> ArticleRecord:
        """Save an article record."""
        db = await self._get_db()

        await db.execute(
            """
            INSERT OR REPLACE INTO articles
            (id, url, title, source, content_hash, first_seen_at, topic, author, published_date, word_count, quality_score, relevance_score, bias_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article.id,
                article.url,
                article.title,
                article.source,
                article.content_hash,
                article.first_seen_at.isoformat(),
                article.topic,
                article.author,
                article.published_date.isoformat() if article.published_date else None,
                article.word_count,
                article.quality_score,
                article.relevance_score,
                article.bias_score,
            ),
        )
        await db.commit()
        return article

    async def get_article(self, article_id: str) -> ArticleRecord | None:
        """Get article by ID."""
        db = await self._get_db()
        cursor = await db.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
        row = await cursor.fetchone()
        await cursor.close()

        if not row:
            return None

        return self._row_to_article(row)

    async def get_article_by_url(self, url: str) -> ArticleRecord | None:
        """Get article by URL."""
        db = await self._get_db()
        cursor = await db.execute("SELECT * FROM articles WHERE url = ?", (url,))
        row = await cursor.fetchone()
        await cursor.close()

        if not row:
            return None

        return self._row_to_article(row)

    def _row_to_article(self, row: aiosqlite.Row) -> ArticleRecord:
        """Convert database row to ArticleRecord."""
        return ArticleRecord(
            id=row["id"],
            url=row["url"],
            title=row["title"],
            source=row["source"],
            content_hash=row["content_hash"],
            first_seen_at=datetime.fromisoformat(row["first_seen_at"]),
            topic=row["topic"],
            author=row["author"],
            published_date=self._parse_datetime(row["published_date"]),
            word_count=row["word_count"],
            quality_score=row["quality_score"],
            relevance_score=row["relevance_score"],
            bias_score=row["bias_score"],
        )

    async def search_articles(
        self,
        query: str | None = None,
        topic: str | None = None,
        source: str | None = None,
        min_quality: float | None = None,
        limit: int = 50,
    ) -> list[ArticleRecord]:
        """Search articles with filters."""
        db = await self._get_db()

        conditions = []
        params: list[Any] = []

        if query:
            conditions.append("(title LIKE ? OR source LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])

        if topic:
            conditions.append("topic = ?")
            params.append(topic)

        if source:
            conditions.append("source LIKE ?")
            params.append(f"%{source}%")

        if min_quality is not None:
            conditions.append("quality_score >= ?")
            params.append(min_quality)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        cursor = await db.execute(
            f"""
            SELECT * FROM articles
            WHERE {where_clause}
            ORDER BY first_seen_at DESC
            LIMIT ?
            """,
            params,
        )
        rows = await cursor.fetchall()
        await cursor.close()

        return [self._row_to_article(row) for row in rows]

    async def get_recent_articles(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> list[ArticleRecord]:
        """Get recently seen articles."""
        db = await self._get_db()
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor = await db.execute(
            """
            SELECT * FROM articles
            WHERE first_seen_at >= ?
            ORDER BY first_seen_at DESC
            LIMIT ?
            """,
            (cutoff, limit),
        )
        rows = await cursor.fetchall()
        await cursor.close()

        return [self._row_to_article(row) for row in rows]

    # Feedback operations
    async def save_feedback(self, feedback: FeedbackRecord) -> FeedbackRecord:
        """Save user feedback."""
        db = await self._get_db()

        await db.execute(
            """
            INSERT INTO feedback
            (id, user_id, digest_id, article_url, feedback_type, created_at, rating, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feedback.id,
                feedback.user_id,
                feedback.digest_id,
                feedback.article_url,
                feedback.feedback_type,
                feedback.created_at.isoformat(),
                feedback.rating,
                feedback.comment,
            ),
        )
        await db.commit()
        return feedback

    async def get_user_feedback(
        self,
        user_id: str,
        limit: int = 100,
    ) -> list[FeedbackRecord]:
        """Get user's feedback history."""
        db = await self._get_db()
        cursor = await db.execute(
            """
            SELECT * FROM feedback
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        await cursor.close()

        return [
            FeedbackRecord(
                id=row["id"],
                user_id=row["user_id"],
                digest_id=row["digest_id"],
                article_url=row["article_url"],
                feedback_type=row["feedback_type"],
                created_at=datetime.fromisoformat(row["created_at"]),
                rating=row["rating"],
                comment=row["comment"],
            )
            for row in rows
        ]

    async def get_article_feedback(self, article_url: str) -> list[FeedbackRecord]:
        """Get all feedback for an article."""
        db = await self._get_db()
        cursor = await db.execute(
            "SELECT * FROM feedback WHERE article_url = ? ORDER BY created_at DESC",
            (article_url,),
        )
        rows = await cursor.fetchall()
        await cursor.close()

        return [
            FeedbackRecord(
                id=row["id"],
                user_id=row["user_id"],
                digest_id=row["digest_id"],
                article_url=row["article_url"],
                feedback_type=row["feedback_type"],
                created_at=datetime.fromisoformat(row["created_at"]),
                rating=row["rating"],
                comment=row["comment"],
            )
            for row in rows
        ]

    # Usage tracking
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
        db = await self._get_db()
        month = datetime.now().strftime("%Y-%m")

        # Try to update existing record
        cursor = await db.execute(
            """
            UPDATE usage
            SET input_tokens = input_tokens + ?,
                output_tokens = output_tokens + ?,
                cost_usd = cost_usd + ?,
                digest_count = digest_count + ?,
                search_count = search_count + ?,
                articles_analyzed = articles_analyzed + ?
            WHERE user_id = ? AND month = ?
            """,
            (input_tokens, output_tokens, cost_usd, digests, searches, articles, user_id, month),
        )
        await db.commit()

        if cursor.rowcount == 0:
            # Insert new record
            usage_id = str(uuid.uuid4())
            await db.execute(
                """
                INSERT INTO usage
                (id, user_id, month, input_tokens, output_tokens, cost_usd, digest_count, search_count, articles_analyzed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (usage_id, user_id, month, input_tokens, output_tokens, cost_usd, digests, searches, articles),
            )
            await db.commit()

        await cursor.close()

        # Return current usage
        usage = await self.get_usage(user_id, month)
        if not usage:
            raise DatabaseError("Failed to record usage")
        return usage

    async def get_usage(self, user_id: str, month: str) -> UsageRecord | None:
        """Get usage for a specific month."""
        db = await self._get_db()
        cursor = await db.execute(
            "SELECT * FROM usage WHERE user_id = ? AND month = ?",
            (user_id, month),
        )
        row = await cursor.fetchone()
        await cursor.close()

        if not row:
            return None

        return UsageRecord(
            id=row["id"],
            user_id=row["user_id"],
            month=row["month"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            cost_usd=row["cost_usd"],
            digest_count=row["digest_count"],
            search_count=row["search_count"],
            articles_analyzed=row["articles_analyzed"],
        )

    async def get_usage_history(
        self,
        user_id: str,
        months: int = 6,
    ) -> list[UsageRecord]:
        """Get usage history for past N months."""
        db = await self._get_db()
        cursor = await db.execute(
            """
            SELECT * FROM usage
            WHERE user_id = ?
            ORDER BY month DESC
            LIMIT ?
            """,
            (user_id, months),
        )
        rows = await cursor.fetchall()
        await cursor.close()

        return [
            UsageRecord(
                id=row["id"],
                user_id=row["user_id"],
                month=row["month"],
                input_tokens=row["input_tokens"],
                output_tokens=row["output_tokens"],
                cost_usd=row["cost_usd"],
                digest_count=row["digest_count"],
                search_count=row["search_count"],
                articles_analyzed=row["articles_analyzed"],
            )
            for row in rows
        ]

    # Statistics
    async def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        db = await self._get_db()

        stats = {}

        # Count users
        cursor = await db.execute("SELECT COUNT(*) as count FROM users")
        row = await cursor.fetchone()
        stats["total_users"] = row["count"] if row else 0
        await cursor.close()

        # Count digests
        cursor = await db.execute("SELECT COUNT(*) as count FROM digests")
        row = await cursor.fetchone()
        stats["total_digests"] = row["count"] if row else 0
        await cursor.close()

        # Count articles
        cursor = await db.execute("SELECT COUNT(*) as count FROM articles")
        row = await cursor.fetchone()
        stats["total_articles"] = row["count"] if row else 0
        await cursor.close()

        # Count feedback
        cursor = await db.execute("SELECT COUNT(*) as count FROM feedback")
        row = await cursor.fetchone()
        stats["total_feedback"] = row["count"] if row else 0
        await cursor.close()

        # Database size
        cursor = await db.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        row = await cursor.fetchone()
        stats["database_size_bytes"] = row["size"] if row else 0
        await cursor.close()

        return stats
