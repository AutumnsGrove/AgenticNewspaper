# Database Documentation

This document describes the database layers for The Daily Clearing.

## Overview

The system uses two database implementations:
- **SQLite**: Local development and testing
- **D1**: Cloudflare's distributed SQLite for production

Both implementations share the same schema and interface.

## Schema

### Users Table

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    subscription_tier TEXT DEFAULT 'free',
    email_verified INTEGER DEFAULT 0,
    api_key TEXT UNIQUE,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_api_key ON users(api_key);
```

### User Preferences Table

```sql
CREATE TABLE user_preferences (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    topics TEXT DEFAULT '[]',           -- JSON array
    delivery_frequency TEXT DEFAULT 'daily_am',
    delivery_time_utc TEXT DEFAULT '06:00',
    channels TEXT DEFAULT '["web"]',    -- JSON array
    timezone TEXT DEFAULT 'UTC',
    tone TEXT DEFAULT 'hn-style',
    skepticism_level INTEGER DEFAULT 3,
    technical_depth INTEGER DEFAULT 3,
    include_bias_analysis INTEGER DEFAULT 1,
    include_connections INTEGER DEFAULT 1,
    max_articles_per_topic INTEGER DEFAULT 5,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### Digests Table

```sql
CREATE TABLE digests (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    subtitle TEXT,
    topics TEXT DEFAULT '[]',           -- JSON array
    article_count INTEGER DEFAULT 0,
    average_quality REAL DEFAULT 0,
    storage_key TEXT,                   -- R2 key for full content
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    published_at TEXT
);

CREATE INDEX idx_digests_user ON digests(user_id);
CREATE INDEX idx_digests_created ON digests(created_at);
```

### Feedback Table

```sql
CREATE TABLE feedback (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    digest_id TEXT NOT NULL REFERENCES digests(id),
    article_id TEXT NOT NULL,
    feedback_type TEXT NOT NULL,        -- 'helpful' or 'not_helpful'
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feedback_user ON feedback(user_id);
CREATE INDEX idx_feedback_article ON feedback(article_id);
```

### Sessions Table

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    token_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(token_hash);
```

### Usage Table

```sql
CREATE TABLE usage (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    action TEXT NOT NULL,
    metadata TEXT,                      -- JSON object
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_usage_user ON usage(user_id);
CREATE INDEX idx_usage_action ON usage(action);
CREATE INDEX idx_usage_date ON usage(created_at);
```

## Python SQLite Implementation

Located at: `packages/core/src/database/sqlite.py`

```python
class SQLiteDatabase:
    """SQLite database layer."""

    def __init__(self, db_path: str = "clearing.db"):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    async def connect(self) -> None:
        """Connect to database and initialize schema."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        await self._init_schema()

    async def get_user(self, user_id: str) -> User | None:
        """Get user by ID."""

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email address."""

    async def create_user(self, user: User) -> User:
        """Create new user."""

    async def update_user(self, user_id: str, updates: dict) -> User:
        """Update user fields."""

    async def get_preferences(self, user_id: str) -> UserPreferences:
        """Get user preferences."""

    async def update_preferences(
        self, user_id: str, updates: dict
    ) -> UserPreferences:
        """Update user preferences."""

    async def create_digest(self, digest: Digest) -> Digest:
        """Create new digest record."""

    async def get_digest(self, digest_id: str) -> Digest | None:
        """Get digest by ID."""

    async def list_digests(
        self, user_id: str, limit: int = 10, offset: int = 0
    ) -> list[Digest]:
        """List user's digests."""

    async def record_feedback(
        self, user_id: str, digest_id: str, article_id: str, feedback: str
    ) -> None:
        """Record article feedback."""

    async def record_usage(
        self, user_id: str, action: str, metadata: dict | None = None
    ) -> None:
        """Record usage event."""
```

## TypeScript D1 Implementation

Located at: `packages/worker/src/services/database.ts`

```typescript
export class D1Database {
  constructor(private db: D1Database) {}

  async getUser(userId: string): Promise<User | null> {
    const result = await this.db
      .prepare('SELECT * FROM users WHERE id = ?')
      .bind(userId)
      .first<UserRow>();
    return result ? this.mapUser(result) : null;
  }

  async createUser(user: CreateUserInput): Promise<User> {
    const id = crypto.randomUUID();
    await this.db
      .prepare(`
        INSERT INTO users (id, email, password_hash, name)
        VALUES (?, ?, ?, ?)
      `)
      .bind(id, user.email, user.passwordHash, user.name)
      .run();
    return this.getUser(id);
  }

  async getPreferences(userId: string): Promise<UserPreferences> {
    const result = await this.db
      .prepare('SELECT * FROM user_preferences WHERE user_id = ?')
      .bind(userId)
      .first<PreferencesRow>();
    return result ? this.mapPreferences(result) : this.defaultPreferences();
  }

  async listDigests(
    userId: string,
    limit = 10,
    offset = 0
  ): Promise<{ digests: DigestSummary[]; total: number }> {
    const [digests, countResult] = await Promise.all([
      this.db
        .prepare(`
          SELECT id, title, created_at, article_count, average_quality
          FROM digests
          WHERE user_id = ?
          ORDER BY created_at DESC
          LIMIT ? OFFSET ?
        `)
        .bind(userId, limit, offset)
        .all<DigestRow>(),
      this.db
        .prepare('SELECT COUNT(*) as count FROM digests WHERE user_id = ?')
        .bind(userId)
        .first<{ count: number }>(),
    ]);

    return {
      digests: digests.results.map(this.mapDigestSummary),
      total: countResult?.count ?? 0,
    };
  }
}
```

## Migrations

Migrations are stored in `packages/worker/schemas/migrations/`.

### Running Migrations

```bash
# Development
wrangler d1 migrations apply clearing-db --local

# Production
wrangler d1 migrations apply clearing-db --remote
```

### Creating New Migrations

```bash
wrangler d1 migrations create clearing-db add_new_table
```

## Data Types

### JSON Fields

Some fields store JSON data:
- `topics`: Array of topic names or topic objects
- `channels`: Array of delivery channels
- `metadata`: Arbitrary JSON object

Parse these fields when reading:
```typescript
const topics = JSON.parse(row.topics || '[]');
```

### Timestamps

All timestamps are stored as ISO 8601 strings in UTC:
```
2025-01-15T10:30:00Z
```

### Boolean Fields

SQLite uses integers for booleans:
- `0` = false
- `1` = true

## Transactions

### SQLite

```python
async with db.transaction():
    await db.create_user(user)
    await db.update_preferences(user.id, prefs)
```

### D1

```typescript
// D1 doesn't support transactions yet
// Use batch operations for atomicity
await db.batch([
  db.prepare('INSERT INTO users ...'),
  db.prepare('INSERT INTO user_preferences ...'),
]);
```

## Performance Considerations

### Indexes

Critical indexes for query performance:
- `users.email` - Login lookups
- `digests.user_id` - User's digest list
- `digests.created_at` - Chronological ordering
- `feedback.article_id` - Learning from feedback

### Pagination

Always use pagination for list queries:
```sql
SELECT * FROM digests
WHERE user_id = ?
ORDER BY created_at DESC
LIMIT 10 OFFSET 0
```

### R2 Offloading

Large digest content is stored in R2, not D1:
- D1 stores metadata only
- R2 stores full article content
- Reduces database size
- Enables CDN caching
