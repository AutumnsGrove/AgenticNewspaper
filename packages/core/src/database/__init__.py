"""Database layer for The Daily Clearing.

Provides a unified interface for:
- SQLite (local development and self-hosted)
- Cloudflare D1 (cloud deployment)

Usage:
    from src.database import get_database, DatabaseType

    # Get local SQLite database
    db = await get_database(DatabaseType.SQLITE, path="data/clearing.db")

    # Get D1 database (in Worker context)
    db = await get_database(DatabaseType.D1, binding=env.DB)

    # Use the database
    await db.save_digest(digest)
    digests = await db.get_user_digests(user_id)
"""

from .base import (
    DatabaseInterface,
    DatabaseType,
    DatabaseError,
    NotFoundError,
    DuplicateError,
)
from .sqlite import SQLiteDatabase
from .factory import get_database, create_sqlite_database

__all__ = [
    # Base
    "DatabaseInterface",
    "DatabaseType",
    "DatabaseError",
    "NotFoundError",
    "DuplicateError",
    # Implementations
    "SQLiteDatabase",
    # Factory
    "get_database",
    "create_sqlite_database",
]
