-- Anonymous User Preferences Table
-- Migration: 0003_anonymous_preferences
-- Created: 2025-12-25

-- ============================================================================
-- Anonymous Preferences Table
-- Stores preferences for unauthenticated users (identified by client-generated UUID)
-- ============================================================================

CREATE TABLE IF NOT EXISTS anonymous_preferences (
  user_id TEXT PRIMARY KEY,
  preferences_json TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_anonymous_prefs_updated ON anonymous_preferences(updated_at);
