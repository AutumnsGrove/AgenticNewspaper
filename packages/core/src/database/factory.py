"""Database factory for creating database instances."""

from typing import Any

from .base import DatabaseInterface, DatabaseType
from .sqlite import SQLiteDatabase


async def get_database(
    db_type: DatabaseType = DatabaseType.SQLITE,
    **kwargs: Any,
) -> DatabaseInterface:
    """
    Get a database instance.

    Args:
        db_type: Type of database to create
        **kwargs: Additional arguments for the specific database type

    Returns:
        Initialized database instance

    Raises:
        ValueError: If database type is not supported
    """
    if db_type == DatabaseType.SQLITE:
        db = create_sqlite_database(**kwargs)
        await db.initialize()
        return db

    elif db_type == DatabaseType.D1:
        # D1 is implemented in the worker package
        # This is a placeholder for the interface
        raise ValueError(
            "D1 database must be used from the worker package. "
            "Import from packages/worker instead."
        )

    elif db_type == DatabaseType.MEMORY:
        # In-memory SQLite for testing
        db = SQLiteDatabase(db_path=":memory:")
        await db.initialize()
        return db

    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def create_sqlite_database(
    path: str = "data/clearing.db",
    **kwargs: Any,
) -> SQLiteDatabase:
    """
    Create a SQLite database instance.

    Args:
        path: Path to database file
        **kwargs: Additional arguments (ignored)

    Returns:
        SQLiteDatabase instance (not initialized)
    """
    return SQLiteDatabase(db_path=path)


# SQL Schema for D1 (Cloudflare)
# This is the same schema as SQLite but formatted for D1 migrations
D1_SCHEMA_SQL = """
-- Migration: 001_initial_schema

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

-- Indexes (D1 compatible)
CREATE INDEX IF NOT EXISTS idx_digests_user ON digests(user_id, generated_at);
CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_topic ON articles(topic);
CREATE INDEX IF NOT EXISTS idx_articles_first_seen ON articles(first_seen_at);
CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_usage_user_month ON usage(user_id, month);
"""


def get_d1_schema() -> str:
    """Get the D1 schema SQL for migrations."""
    return D1_SCHEMA_SQL
