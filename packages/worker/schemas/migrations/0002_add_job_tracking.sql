-- Migration: Add job tracking for ephemeral digest generation
-- Created: 2025-12-25

-- Jobs table: tracks digest generation jobs and server lifecycle
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN (
    'pending',
    'provisioning',
    'installing',
    'running',
    'uploading',
    'destroying',
    'completed',
    'failed'
  )),
  server_id TEXT,
  server_ip TEXT,
  started_at TEXT NOT NULL,
  completed_at TEXT,
  error TEXT,

  -- Job metadata
  topics_count INTEGER,
  articles_found INTEGER,
  articles_included INTEGER,
  tokens_used INTEGER,
  cost_usd REAL,

  -- Output
  digest_r2_key TEXT,

  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_started ON jobs(started_at);
CREATE INDEX IF NOT EXISTS idx_jobs_server ON jobs(server_id);

-- Server logs table: detailed lifecycle logging
CREATE TABLE IF NOT EXISTS server_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL,
  timestamp TEXT NOT NULL DEFAULT (datetime('now')),
  level TEXT NOT NULL CHECK(level IN ('info', 'warn', 'error')),
  message TEXT NOT NULL,
  metadata TEXT, -- JSON blob

  FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_logs_job ON server_logs(job_id);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON server_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_level ON server_logs(level);
