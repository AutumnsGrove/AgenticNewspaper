/**
 * UserState Durable Object.
 *
 * Manages per-user preferences, history, and personalization data.
 * Each user has their own UserState instance for isolation.
 */

import type { Env, UserPreferences, FeedbackType } from '../types';

// FeedbackRecord for mapping SQL results
// interface FeedbackRecord {
//   id: string;
//   digest_id: string;
//   article_url: string | null;
//   feedback_type: string;
//   notes: string | null;
//   created_at: string;
// }

interface DigestHistoryRecord {
  digest_id: string;
  generated_at: string;
  topics_json: string;
  article_count: number;
  cost_usd: number;
  r2_key: string;
}

export class UserState implements DurableObject {
  private state: DurableObjectState;
  private _env: Env;
  private sql: SqlStorage;

  constructor(state: DurableObjectState, env: Env) {
    this.state = state;
    this._env = env;
    void this._env; // Reserved for future use
    this.sql = state.storage.sql;

    // Initialize SQLite schema on first access
    this.state.blockConcurrencyWhile(async () => {
      await this.initializeSchema();
    });
  }

  private async initializeSchema(): Promise<void> {
    this.sql.exec(`
      -- User preferences (single row per user)
      CREATE TABLE IF NOT EXISTS preferences (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        preferences_json TEXT NOT NULL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
      );

      -- Digest history
      CREATE TABLE IF NOT EXISTS digest_history (
        digest_id TEXT PRIMARY KEY,
        generated_at TEXT NOT NULL,
        topics_json TEXT,
        article_count INTEGER,
        cost_usd REAL,
        r2_key TEXT
      );

      -- Feedback for learning
      CREATE TABLE IF NOT EXISTS feedback (
        id TEXT PRIMARY KEY,
        digest_id TEXT,
        article_url TEXT,
        feedback_type TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
      );

      -- Topic weights learned from feedback
      CREATE TABLE IF NOT EXISTS topic_weights (
        topic TEXT PRIMARY KEY,
        weight REAL DEFAULT 1.0,
        interactions INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
      );

      -- Source weights learned from feedback
      CREATE TABLE IF NOT EXISTS source_weights (
        source TEXT PRIMARY KEY,
        weight REAL DEFAULT 1.0,
        interactions INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
      );

      -- Indexes
      CREATE INDEX IF NOT EXISTS idx_digest_history_date ON digest_history(generated_at DESC);
      CREATE INDEX IF NOT EXISTS idx_feedback_digest ON feedback(digest_id);
      CREATE INDEX IF NOT EXISTS idx_feedback_article ON feedback(article_url);
    `);
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    try {
      switch (request.method) {
        case 'GET':
          if (path === '/preferences') {
            return this.getPreferences();
          }
          if (path === '/history') {
            return this.getHistory(url);
          }
          if (path === '/weights') {
            return this.getWeights();
          }
          if (path === '/stats') {
            return this.getStats();
          }
          break;

        case 'PUT':
          if (path === '/preferences') {
            return await this.updatePreferences(request);
          }
          break;

        case 'POST':
          if (path === '/feedback') {
            return await this.addFeedback(request);
          }
          if (path === '/digest') {
            return await this.recordDigest(request);
          }
          break;

        case 'DELETE':
          if (path === '/history') {
            return await this.clearHistory();
          }
          break;
      }

      return new Response('Not Found', { status: 404 });
    } catch (error) {
      console.error('UserState error:', error);
      return new Response(
        JSON.stringify({
          success: false,
          error: {
            code: 'INTERNAL_ERROR',
            message: error instanceof Error ? error.message : 'Unknown error',
          },
        }),
        {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }
  }

  private getPreferences(): Response {
    const row = this.sql.exec('SELECT preferences_json FROM preferences WHERE id = 1').one() as {
      preferences_json: string;
    } | null;

    const preferences = row ? JSON.parse(row.preferences_json) : this.getDefaultPreferences();

    return new Response(
      JSON.stringify({
        success: true,
        data: preferences,
      }),
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private getDefaultPreferences(): UserPreferences {
    return {
      topics: [
        {
          name: 'AI & Machine Learning',
          keywords: ['artificial intelligence', 'machine learning', 'LLM', 'neural network'],
          priority: 5,
          enabled: true,
        },
        {
          name: 'Science Breakthroughs',
          keywords: ['research', 'discovery', 'peer-reviewed', 'study'],
          priority: 4,
          enabled: true,
        },
        {
          name: 'Programming & Dev Tools',
          keywords: ['programming', 'framework', 'library', 'open source'],
          priority: 4,
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

  private async updatePreferences(request: Request): Promise<Response> {
    const preferences = (await request.json()) as UserPreferences;
    const now = new Date().toISOString();

    this.sql.exec(
      `INSERT OR REPLACE INTO preferences (id, preferences_json, updated_at)
       VALUES (1, ?, ?)`,
      JSON.stringify(preferences),
      now
    );

    return new Response(
      JSON.stringify({
        success: true,
        data: preferences,
      }),
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private getHistory(url: URL): Response {
    const limit = parseInt(url.searchParams.get('limit') || '20', 10);
    const offset = parseInt(url.searchParams.get('offset') || '0', 10);

    const rows = this.sql
      .exec(
        `SELECT * FROM digest_history
         ORDER BY generated_at DESC
         LIMIT ? OFFSET ?`,
        limit,
        offset
      )
      .toArray() as unknown as DigestHistoryRecord[];

    const countRow = this.sql.exec('SELECT COUNT(*) as cnt FROM digest_history').one() as {
      cnt: number;
    };

    const digests = rows.map((row) => ({
      digestId: row.digest_id,
      generatedAt: row.generated_at,
      topics: JSON.parse(row.topics_json || '[]'),
      articleCount: row.article_count,
      costUsd: row.cost_usd,
      r2Key: row.r2_key,
    }));

    return new Response(
      JSON.stringify({
        success: true,
        data: digests,
        pagination: {
          page: Math.floor(offset / limit) + 1,
          pageSize: limit,
          total: countRow.cnt,
          totalPages: Math.ceil(countRow.cnt / limit),
          hasNext: offset + limit < countRow.cnt,
          hasPrev: offset > 0,
        },
      }),
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private async recordDigest(request: Request): Promise<Response> {
    const digest = (await request.json()) as {
      digestId: string;
      generatedAt: string;
      topics: string[];
      articleCount: number;
      costUsd: number;
      r2Key: string;
    };

    this.sql.exec(
      `INSERT INTO digest_history (digest_id, generated_at, topics_json, article_count, cost_usd, r2_key)
       VALUES (?, ?, ?, ?, ?, ?)`,
      digest.digestId,
      digest.generatedAt,
      JSON.stringify(digest.topics),
      digest.articleCount,
      digest.costUsd,
      digest.r2Key
    );

    return new Response(
      JSON.stringify({
        success: true,
        data: { digestId: digest.digestId },
      }),
      {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private async addFeedback(request: Request): Promise<Response> {
    const feedback = (await request.json()) as {
      id: string;
      digestId: string;
      articleUrl?: string;
      type: FeedbackType;
      notes?: string;
    };

    const now = new Date().toISOString();

    this.sql.exec(
      `INSERT INTO feedback (id, digest_id, article_url, feedback_type, notes, created_at)
       VALUES (?, ?, ?, ?, ?, ?)`,
      feedback.id,
      feedback.digestId,
      feedback.articleUrl || null,
      feedback.type,
      feedback.notes || null,
      now
    );

    // Update weights based on feedback
    await this.updateWeightsFromFeedback(feedback);

    return new Response(
      JSON.stringify({
        success: true,
        data: { id: feedback.id },
      }),
      {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private async updateWeightsFromFeedback(feedback: {
    type: FeedbackType;
    articleUrl?: string;
    digestId?: string;
  }): Promise<void> {
    // Weight adjustments based on feedback type
    const weightAdjustments: Record<FeedbackType, number> = {
      like: 0.1,
      dislike: -0.15,
      read: 0.05,
      skip: -0.05,
      share: 0.2,
      save: 0.15,
    };

    const adjustment = weightAdjustments[feedback.type];

    // If we have article URL, we could extract source and update source_weights
    // For now, just record the feedback - more sophisticated learning would be added later
    if (feedback.articleUrl) {
      try {
        const url = new URL(feedback.articleUrl);
        const source = url.hostname;
        const now = new Date().toISOString();

        // Upsert source weight
        this.sql.exec(
          `INSERT INTO source_weights (source, weight, interactions, updated_at)
           VALUES (?, 1.0 + ?, 1, ?)
           ON CONFLICT(source) DO UPDATE SET
             weight = MIN(2.0, MAX(0.1, weight + ?)),
             interactions = interactions + 1,
             updated_at = ?`,
          source,
          adjustment,
          now,
          adjustment,
          now
        );
      } catch {
        // Invalid URL, skip weight update
      }
    }
  }

  private getWeights(): Response {
    const topicWeights = this.sql.exec('SELECT * FROM topic_weights ORDER BY weight DESC').toArray();
    const sourceWeights = this.sql
      .exec('SELECT * FROM source_weights ORDER BY weight DESC')
      .toArray();

    return new Response(
      JSON.stringify({
        success: true,
        data: {
          topics: topicWeights,
          sources: sourceWeights,
        },
      }),
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private getStats(): Response {
    const digestCount = (
      this.sql.exec('SELECT COUNT(*) as cnt FROM digest_history').one() as { cnt: number }
    ).cnt;
    const feedbackCount = (this.sql.exec('SELECT COUNT(*) as cnt FROM feedback').one() as { cnt: number })
      .cnt;
    const totalCost = (
      this.sql.exec('SELECT COALESCE(SUM(cost_usd), 0) as total FROM digest_history').one() as {
        total: number;
      }
    ).total;
    const totalArticles = (
      this.sql
        .exec('SELECT COALESCE(SUM(article_count), 0) as total FROM digest_history')
        .one() as { total: number }
    ).total;

    const feedbackBreakdown = this.sql
      .exec(
        `SELECT feedback_type, COUNT(*) as cnt
         FROM feedback
         GROUP BY feedback_type`
      )
      .toArray() as { feedback_type: string; cnt: number }[];

    return new Response(
      JSON.stringify({
        success: true,
        data: {
          digestCount,
          feedbackCount,
          totalCostUsd: totalCost,
          totalArticles,
          feedbackBreakdown: Object.fromEntries(
            feedbackBreakdown.map((r) => [r.feedback_type, r.cnt])
          ),
        },
      }),
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private async clearHistory(): Promise<Response> {
    this.sql.exec('DELETE FROM digest_history');
    this.sql.exec('DELETE FROM feedback');

    return new Response(
      JSON.stringify({
        success: true,
      }),
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
