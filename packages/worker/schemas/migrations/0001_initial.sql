-- Initial D1 Schema for The Daily Clearing
-- Migration: 0001_initial
-- Created: 2025-12-25

-- ============================================================================
-- Users Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  subscription_tier TEXT DEFAULT 'free' CHECK (subscription_tier IN ('free', 'basic', 'pro')),
  preferences_json TEXT,
  rss_token TEXT UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_rss_token ON users(rss_token);

-- ============================================================================
-- Digests Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS digests (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  generated_at TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  frequency TEXT NOT NULL,
  r2_key TEXT NOT NULL,
  article_count INTEGER DEFAULT 0,
  topics_json TEXT,
  cost_usd REAL DEFAULT 0,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_digests_user ON digests(user_id, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_digests_generated ON digests(generated_at DESC);

-- ============================================================================
-- Feedback Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS feedback (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  digest_id TEXT NOT NULL,
  article_url TEXT,
  feedback_type TEXT NOT NULL CHECK (feedback_type IN ('like', 'dislike', 'read', 'skip', 'share', 'save')),
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (digest_id) REFERENCES digests(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_digest ON feedback(digest_id);
CREATE INDEX IF NOT EXISTS idx_feedback_article ON feedback(article_url);

-- ============================================================================
-- Usage Tracking Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS usage (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  month TEXT NOT NULL,
  input_tokens INTEGER DEFAULT 0,
  output_tokens INTEGER DEFAULT 0,
  cost_usd REAL DEFAULT 0,
  digest_count INTEGER DEFAULT 0,
  articles_fetched INTEGER DEFAULT 0,
  articles_analyzed INTEGER DEFAULT 0,
  UNIQUE(user_id, month),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_usage_user_month ON usage(user_id, month);

-- ============================================================================
-- Sessions Table (for auth tokens)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  expires_at TEXT NOT NULL,
  user_agent TEXT,
  ip_address TEXT,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);

-- ============================================================================
-- Scheduled Jobs Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS scheduled_jobs (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  job_type TEXT NOT NULL CHECK (job_type IN ('digest', 'email', 'cleanup')),
  scheduled_for TEXT NOT NULL,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
  created_at TEXT DEFAULT (datetime('now')),
  started_at TEXT,
  completed_at TEXT,
  error_message TEXT,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_pending ON scheduled_jobs(scheduled_for, status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_user ON scheduled_jobs(user_id, created_at DESC);

-- ============================================================================
-- Article Cache Table (for deduplication)
-- ============================================================================

CREATE TABLE IF NOT EXISTS article_cache (
  url_hash TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  title TEXT,
  content_hash TEXT,
  first_seen_at TEXT DEFAULT (datetime('now')),
  last_seen_at TEXT DEFAULT (datetime('now')),
  fetch_count INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_article_cache_url ON article_cache(url);
CREATE INDEX IF NOT EXISTS idx_article_cache_content ON article_cache(content_hash);
