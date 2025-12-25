/**
 * D1 Database Service.
 *
 * Handles user accounts, digest records, feedback, and usage tracking.
 */

import type { Env, User, UserPreferences, Feedback, UsageRecord, FeedbackType } from '../types';

// ============================================================================
// User Operations
// ============================================================================

/**
 * Create a new user.
 */
export async function createUser(
  db: D1Database,
  data: {
    id: string;
    email: string;
    subscriptionTier?: 'free' | 'basic' | 'pro';
    preferences?: UserPreferences;
    rssToken?: string;
  }
): Promise<User> {
  const now = new Date().toISOString();

  await db
    .prepare(
      `INSERT INTO users (id, email, created_at, subscription_tier, preferences_json, rss_token)
       VALUES (?, ?, ?, ?, ?, ?)`
    )
    .bind(
      data.id,
      data.email,
      now,
      data.subscriptionTier || 'free',
      data.preferences ? JSON.stringify(data.preferences) : null,
      data.rssToken || null
    )
    .run();

  return {
    id: data.id,
    email: data.email,
    createdAt: now,
    subscriptionTier: data.subscriptionTier || 'free',
    preferences: data.preferences || getDefaultPreferences(),
    rssToken: data.rssToken,
  };
}

/**
 * Get user by ID.
 */
export async function getUserById(db: D1Database, userId: string): Promise<User | null> {
  const result = await db.prepare('SELECT * FROM users WHERE id = ?').bind(userId).first();

  if (!result) {
    return null;
  }

  return mapUserRow(result);
}

/**
 * Get user by email.
 */
export async function getUserByEmail(db: D1Database, email: string): Promise<User | null> {
  const result = await db.prepare('SELECT * FROM users WHERE email = ?').bind(email).first();

  if (!result) {
    return null;
  }

  return mapUserRow(result);
}

/**
 * Get user by RSS token.
 */
export async function getUserByRssToken(db: D1Database, token: string): Promise<User | null> {
  const result = await db.prepare('SELECT * FROM users WHERE rss_token = ?').bind(token).first();

  if (!result) {
    return null;
  }

  return mapUserRow(result);
}

/**
 * Update user preferences.
 */
export async function updateUserPreferences(
  db: D1Database,
  userId: string,
  preferences: UserPreferences
): Promise<void> {
  await db
    .prepare('UPDATE users SET preferences_json = ? WHERE id = ?')
    .bind(JSON.stringify(preferences), userId)
    .run();
}

/**
 * Update user subscription tier.
 */
export async function updateUserTier(
  db: D1Database,
  userId: string,
  tier: 'free' | 'basic' | 'pro'
): Promise<void> {
  await db.prepare('UPDATE users SET subscription_tier = ? WHERE id = ?').bind(tier, userId).run();
}

/**
 * Generate and set RSS token for user.
 */
export async function generateRssToken(db: D1Database, userId: string): Promise<string> {
  const token = crypto.randomUUID();
  await db.prepare('UPDATE users SET rss_token = ? WHERE id = ?').bind(token, userId).run();
  return token;
}

/**
 * Delete user and all associated data.
 */
export async function deleteUser(db: D1Database, userId: string): Promise<void> {
  // Delete in order to respect foreign keys
  await db.prepare('DELETE FROM feedback WHERE user_id = ?').bind(userId).run();
  await db.prepare('DELETE FROM usage WHERE user_id = ?').bind(userId).run();
  await db.prepare('DELETE FROM digests WHERE user_id = ?').bind(userId).run();
  await db.prepare('DELETE FROM users WHERE id = ?').bind(userId).run();
}

// ============================================================================
// Digest Record Operations
// ============================================================================

export interface DigestRecord {
  id: string;
  userId: string;
  generatedAt: string;
  periodStart: string;
  periodEnd: string;
  frequency: string;
  r2Key: string;
  articleCount: number;
  topics: string[];
  costUsd: number;
}

/**
 * Create a digest record.
 */
export async function createDigestRecord(
  db: D1Database,
  data: {
    id: string;
    userId: string;
    generatedAt: string;
    periodStart: string;
    periodEnd: string;
    frequency: string;
    r2Key: string;
    articleCount: number;
    topics: string[];
    costUsd: number;
  }
): Promise<DigestRecord> {
  await db
    .prepare(
      `INSERT INTO digests (id, user_id, generated_at, period_start, period_end, frequency, r2_key, article_count, topics_json, cost_usd)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    )
    .bind(
      data.id,
      data.userId,
      data.generatedAt,
      data.periodStart,
      data.periodEnd,
      data.frequency,
      data.r2Key,
      data.articleCount,
      JSON.stringify(data.topics),
      data.costUsd
    )
    .run();

  return data;
}

/**
 * Get digest record by ID.
 */
export async function getDigestRecord(db: D1Database, digestId: string): Promise<DigestRecord | null> {
  const result = await db.prepare('SELECT * FROM digests WHERE id = ?').bind(digestId).first();

  if (!result) {
    return null;
  }

  return mapDigestRow(result);
}

/**
 * List user's digest records with pagination.
 */
export async function listUserDigestRecords(
  db: D1Database,
  userId: string,
  options: { limit?: number; offset?: number } = {}
): Promise<{ records: DigestRecord[]; total: number }> {
  const { limit = 20, offset = 0 } = options;

  const [recordsResult, countResult] = await Promise.all([
    db
      .prepare(
        `SELECT * FROM digests WHERE user_id = ? ORDER BY generated_at DESC LIMIT ? OFFSET ?`
      )
      .bind(userId, limit, offset)
      .all(),
    db.prepare('SELECT COUNT(*) as count FROM digests WHERE user_id = ?').bind(userId).first(),
  ]);

  return {
    records: recordsResult.results.map(mapDigestRow),
    total: (countResult?.count as number) || 0,
  };
}

// ============================================================================
// Feedback Operations
// ============================================================================

/**
 * Create feedback record.
 */
export async function createFeedback(
  db: D1Database,
  data: {
    id: string;
    userId: string;
    digestId: string;
    articleUrl?: string;
    type: FeedbackType;
  }
): Promise<Feedback> {
  const now = new Date().toISOString();

  await db
    .prepare(
      `INSERT INTO feedback (id, user_id, digest_id, article_url, feedback_type, created_at)
       VALUES (?, ?, ?, ?, ?, ?)`
    )
    .bind(data.id, data.userId, data.digestId, data.articleUrl || null, data.type, now)
    .run();

  return {
    id: data.id,
    userId: data.userId,
    digestId: data.digestId,
    articleUrl: data.articleUrl,
    type: data.type,
    createdAt: now,
  };
}

/**
 * Get user's feedback for a digest.
 */
export async function getDigestFeedback(
  db: D1Database,
  userId: string,
  digestId: string
): Promise<Feedback[]> {
  const result = await db
    .prepare('SELECT * FROM feedback WHERE user_id = ? AND digest_id = ?')
    .bind(userId, digestId)
    .all();

  return result.results.map(mapFeedbackRow);
}

// ============================================================================
// Usage Tracking Operations
// ============================================================================

/**
 * Get or create usage record for month.
 */
export async function getOrCreateUsage(
  db: D1Database,
  userId: string,
  month: string
): Promise<UsageRecord> {
  let result = await db
    .prepare('SELECT * FROM usage WHERE user_id = ? AND month = ?')
    .bind(userId, month)
    .first();

  if (!result) {
    const id = crypto.randomUUID();
    await db
      .prepare(
        `INSERT INTO usage (id, user_id, month, input_tokens, output_tokens, cost_usd, digest_count)
         VALUES (?, ?, ?, 0, 0, 0, 0)`
      )
      .bind(id, userId, month)
      .run();

    result = {
      user_id: userId,
      month,
      input_tokens: 0,
      output_tokens: 0,
      cost_usd: 0,
      digest_count: 0,
      articles_fetched: 0,
      articles_analyzed: 0,
    };
  }

  return mapUsageRow(result);
}

/**
 * Increment usage counters.
 */
export async function incrementUsage(
  db: D1Database,
  userId: string,
  month: string,
  data: {
    inputTokens?: number;
    outputTokens?: number;
    costUsd?: number;
    digestCount?: number;
    articlesFetched?: number;
    articlesAnalyzed?: number;
  }
): Promise<void> {
  // Ensure record exists
  await getOrCreateUsage(db, userId, month);

  const updates: string[] = [];
  const values: (string | number)[] = [];

  if (data.inputTokens) {
    updates.push('input_tokens = input_tokens + ?');
    values.push(data.inputTokens);
  }
  if (data.outputTokens) {
    updates.push('output_tokens = output_tokens + ?');
    values.push(data.outputTokens);
  }
  if (data.costUsd) {
    updates.push('cost_usd = cost_usd + ?');
    values.push(data.costUsd);
  }
  if (data.digestCount) {
    updates.push('digest_count = digest_count + ?');
    values.push(data.digestCount);
  }
  if (data.articlesFetched) {
    updates.push('articles_fetched = articles_fetched + ?');
    values.push(data.articlesFetched);
  }
  if (data.articlesAnalyzed) {
    updates.push('articles_analyzed = articles_analyzed + ?');
    values.push(data.articlesAnalyzed);
  }

  if (updates.length > 0) {
    await db
      .prepare(`UPDATE usage SET ${updates.join(', ')} WHERE user_id = ? AND month = ?`)
      .bind(...values, userId, month)
      .run();
  }
}

/**
 * Get usage history for user.
 */
export async function getUserUsageHistory(
  db: D1Database,
  userId: string,
  months: number = 6
): Promise<UsageRecord[]> {
  const result = await db
    .prepare(
      `SELECT * FROM usage WHERE user_id = ? ORDER BY month DESC LIMIT ?`
    )
    .bind(userId, months)
    .all();

  return result.results.map(mapUsageRow);
}

// ============================================================================
// Helper Functions
// ============================================================================

function getDefaultPreferences(): UserPreferences {
  return {
    topics: [
      {
        name: 'AI & Machine Learning',
        keywords: ['artificial intelligence', 'machine learning', 'LLM', 'neural network'],
        priority: 5,
        enabled: true,
      },
    ],
    sources: [],
    delivery: {
      frequency: 'daily_am',
      deliveryTimeUtc: '06:00',
      channels: ['web'],
      lookbackHours: 24,
      timezone: 'UTC',
    },
    style: {
      tone: 'hn-style',
      skepticismLevel: 3,
      technicalDepth: 3,
      includeBiasAnalysis: true,
      includeCrossConnections: true,
      maxArticlesPerTopic: 5,
    },
    thresholds: {
      minRelevanceScore: 0.6,
      minQualityScore: 0.5,
      minNoveltyScore: 0.3,
      maxBiasScore: 0.8,
    },
  };
}

function mapUserRow(row: Record<string, unknown>): User {
  return {
    id: row.id as string,
    email: row.email as string,
    createdAt: row.created_at as string,
    subscriptionTier: (row.subscription_tier as 'free' | 'basic' | 'pro') || 'free',
    preferences: row.preferences_json
      ? JSON.parse(row.preferences_json as string)
      : getDefaultPreferences(),
    rssToken: row.rss_token as string | undefined,
  };
}

function mapDigestRow(row: Record<string, unknown>): DigestRecord {
  return {
    id: row.id as string,
    userId: row.user_id as string,
    generatedAt: row.generated_at as string,
    periodStart: row.period_start as string,
    periodEnd: row.period_end as string,
    frequency: row.frequency as string,
    r2Key: row.r2_key as string,
    articleCount: row.article_count as number,
    topics: row.topics_json ? JSON.parse(row.topics_json as string) : [],
    costUsd: row.cost_usd as number,
  };
}

function mapFeedbackRow(row: Record<string, unknown>): Feedback {
  return {
    id: row.id as string,
    userId: row.user_id as string,
    digestId: row.digest_id as string,
    articleUrl: row.article_url as string | undefined,
    type: row.feedback_type as FeedbackType,
    createdAt: row.created_at as string,
  };
}

function mapUsageRow(row: Record<string, unknown>): UsageRecord {
  return {
    userId: row.user_id as string,
    month: row.month as string,
    inputTokens: (row.input_tokens as number) || 0,
    outputTokens: (row.output_tokens as number) || 0,
    costUsd: (row.cost_usd as number) || 0,
    digestCount: (row.digest_count as number) || 0,
    articlesFetched: (row.articles_fetched as number) || 0,
    articlesAnalyzed: (row.articles_analyzed as number) || 0,
  };
}
