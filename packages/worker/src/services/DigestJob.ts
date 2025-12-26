/**
 * DigestJob Durable Object.
 *
 * Manages per-user digest generation state and processing.
 * Each user has their own DigestJob instance for isolation.
 */

import type { Env, DigestJobState, DigestJobProgress, JobStatus } from '../types';

// StoredArticle interface matches SQL table schema
// Used for mapping SQL results in getArticles()
// interface StoredArticle {
//   id: string;
//   url: string;
//   title: string;
//   content: string;
//   source: string;
//   topic: string;
//   relevanceScore: number;
//   qualityScore: number;
//   biasDirection: string;
//   keyPointsJson: string;
//   fetchedAt: string;
// }

// Artifact interface for future use with intermediate artifacts
// interface Artifact {
//   id: number;
//   artifactType: 'search_results' | 'synthesis_draft' | 'final_digest';
//   content: string;
//   createdAt: string;
// }

export class DigestJob implements DurableObject {
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
    // Create tables if they don't exist
    this.sql.exec(`
      -- Single row tracking current generation
      CREATE TABLE IF NOT EXISTS digest_job (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        batch_num INTEGER DEFAULT 0,
        articles_found INTEGER DEFAULT 0,
        articles_parsed INTEGER DEFAULT 0,
        articles_analyzed INTEGER DEFAULT 0,
        current_topic TEXT,
        error_message TEXT,
        started_at TEXT,
        updated_at TEXT,
        completed_at TEXT,
        digest_id TEXT
      );

      -- Accumulated articles for current job
      CREATE TABLE IF NOT EXISTS articles (
        id TEXT PRIMARY KEY,
        url TEXT UNIQUE,
        title TEXT,
        content TEXT,
        source TEXT,
        topic TEXT,
        relevance_score REAL,
        quality_score REAL,
        bias_direction TEXT,
        key_points_json TEXT,
        fetched_at TEXT
      );

      -- Processing artifacts
      CREATE TABLE IF NOT EXISTS artifacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artifact_type TEXT,
        content TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
      );

      -- Indexes
      CREATE INDEX IF NOT EXISTS idx_articles_topic ON articles(topic);
      CREATE INDEX IF NOT EXISTS idx_articles_quality ON articles(quality_score DESC);
      CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(artifact_type);
    `);
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    try {
      switch (request.method) {
        case 'GET':
          if (path === '/status') {
            return this.getStatus();
          }
          if (path === '/progress') {
            return this.getProgress();
          }
          if (path === '/articles') {
            return this.getArticles();
          }
          break;

        case 'POST':
          if (path === '/start') {
            return await this.startJob(request);
          }
          if (path === '/add-article') {
            return await this.addArticle(request);
          }
          if (path === '/update-status') {
            return await this.updateStatus(request);
          }
          if (path === '/add-artifact') {
            return await this.addArtifact(request);
          }
          if (path === '/complete') {
            return await this.completeJob(request);
          }
          if (path === '/fail') {
            return await this.failJob(request);
          }
          break;

        case 'DELETE':
          if (path === '/reset') {
            return await this.resetJob();
          }
          break;
      }

      return new Response('Not Found', { status: 404 });
    } catch (error) {
      console.error('DigestJob error:', error);
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

  private getStatus(): Response {
    const row = this.sql.exec('SELECT * FROM digest_job LIMIT 1').one();
    const job = row ? this.mapJobRow(row as unknown as Record<string, unknown>) : null;

    if (!job) {
      return new Response(
        JSON.stringify({
          success: true,
          data: null,
        }),
        {
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    return new Response(
      JSON.stringify({
        success: true,
        data: job,
      }),
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private getProgress(): Response {
    const row = this.sql.exec('SELECT * FROM digest_job LIMIT 1').one();
    const job = row ? this.mapJobRow(row as unknown as Record<string, unknown>) : null;

    if (!job) {
      return new Response(
        JSON.stringify({
          success: true,
          data: {
            status: 'idle',
            progress: 0,
            currentStep: 'No active job',
            articlesFound: 0,
            articlesAnalyzed: 0,
          },
        }),
        {
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    const progress = this.calculateProgress(job as unknown as Record<string, unknown>);

    return new Response(
      JSON.stringify({
        success: true,
        data: progress,
      }),
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private calculateProgress(job: Record<string, unknown>): DigestJobProgress {
    const status = job.status as JobStatus;
    const articlesFound = (job.articles_found as number) || 0;
    const articlesAnalyzed = (job.articles_analyzed as number) || 0;

    // Progress weights by stage
    const stageWeights: Record<JobStatus, { base: number; max: number }> = {
      pending: { base: 0, max: 5 },
      searching: { base: 5, max: 20 },
      fetching: { base: 20, max: 40 },
      parsing: { base: 40, max: 55 },
      analyzing: { base: 55, max: 85 },
      synthesizing: { base: 85, max: 99 },
      complete: { base: 100, max: 100 },
      failed: { base: 0, max: 0 },
    };

    const stage = stageWeights[status] || { base: 0, max: 0 };
    let progress = stage.base;

    // Interpolate within stage based on articles processed
    if (status === 'analyzing' && articlesFound > 0) {
      const stageProgress = articlesAnalyzed / articlesFound;
      progress = stage.base + (stage.max - stage.base) * stageProgress;
    }

    const stepDescriptions: Record<JobStatus, string> = {
      pending: 'Initializing...',
      searching: `Searching for articles on ${job.current_topic || 'topics'}...`,
      fetching: `Fetching ${articlesFound} articles...`,
      parsing: 'Parsing article content...',
      analyzing: `Analyzing articles (${articlesAnalyzed}/${articlesFound})...`,
      synthesizing: 'Synthesizing digest...',
      complete: 'Digest complete!',
      failed: job.error_message as string || 'Job failed',
    };

    return {
      status,
      progress: Math.round(progress),
      currentStep: stepDescriptions[status],
      articlesFound,
      articlesAnalyzed,
    };
  }

  private getArticles(): Response {
    const rows = this.sql
      .exec('SELECT * FROM articles ORDER BY quality_score DESC')
      .toArray();

    // Map snake_case SQL columns to camelCase
    const mapped = rows.map((row) => {
      const a = row as unknown as Record<string, unknown>;
      return {
        id: a.id as string,
        url: a.url as string,
        title: a.title as string,
        content: a.content as string,
        source: a.source as string,
        topic: a.topic as string,
        relevanceScore: a.relevance_score as number,
        qualityScore: a.quality_score as number,
        biasDirection: a.bias_direction as string,
        keyPoints: JSON.parse((a.key_points_json as string) || '[]'),
        fetchedAt: a.fetched_at as string,
      };
    });

    return new Response(
      JSON.stringify({
        success: true,
        data: mapped,
      }),
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private async startJob(request: Request): Promise<Response> {
    const body = (await request.json()) as { userId: string; jobId: string };
    const { userId, jobId } = body;

    // Clear any existing job data
    this.sql.exec('DELETE FROM digest_job');
    this.sql.exec('DELETE FROM articles');
    this.sql.exec('DELETE FROM artifacts');

    // Create new job
    const now = new Date().toISOString();
    this.sql.exec(
      `INSERT INTO digest_job (id, user_id, status, started_at, updated_at)
       VALUES (?, ?, 'pending', ?, ?)`,
      jobId,
      userId,
      now,
      now
    );

    return new Response(
      JSON.stringify({
        success: true,
        data: {
          id: jobId,
          userId,
          status: 'pending',
          startedAt: now,
        },
      }),
      {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private async updateStatus(request: Request): Promise<Response> {
    const body = (await request.json()) as {
      status: JobStatus;
      currentTopic?: string;
      articlesFound?: number;
      articlesParsed?: number;
      articlesAnalyzed?: number;
    };

    const updates: string[] = ['status = ?', 'updated_at = ?'];
    const values: (string | number)[] = [body.status, new Date().toISOString()];

    if (body.currentTopic !== undefined) {
      updates.push('current_topic = ?');
      values.push(body.currentTopic);
    }
    if (body.articlesFound !== undefined) {
      updates.push('articles_found = ?');
      values.push(body.articlesFound);
    }
    if (body.articlesParsed !== undefined) {
      updates.push('articles_parsed = ?');
      values.push(body.articlesParsed);
    }
    if (body.articlesAnalyzed !== undefined) {
      updates.push('articles_analyzed = ?');
      values.push(body.articlesAnalyzed);
    }

    this.sql.exec(`UPDATE digest_job SET ${updates.join(', ')}`, ...values);

    return new Response(
      JSON.stringify({
        success: true,
        data: { status: body.status },
      }),
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private async addArticle(request: Request): Promise<Response> {
    const article = (await request.json()) as {
      id: string;
      url: string;
      title: string;
      content: string;
      source: string;
      topic: string;
      relevanceScore: number;
      qualityScore: number;
      biasDirection: string;
      keyPoints: string[];
    };

    this.sql.exec(
      `INSERT OR REPLACE INTO articles
       (id, url, title, content, source, topic, relevance_score, quality_score, bias_direction, key_points_json, fetched_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      article.id,
      article.url,
      article.title,
      article.content,
      article.source,
      article.topic,
      article.relevanceScore,
      article.qualityScore,
      article.biasDirection,
      JSON.stringify(article.keyPoints),
      new Date().toISOString()
    );

    // Update count
    const count = this.sql.exec('SELECT COUNT(*) as cnt FROM articles').one() as { cnt: number };
    this.sql.exec(
      'UPDATE digest_job SET articles_found = ?, updated_at = ?',
      count.cnt,
      new Date().toISOString()
    );

    return new Response(
      JSON.stringify({
        success: true,
        data: { id: article.id },
      }),
      {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private async addArtifact(request: Request): Promise<Response> {
    const body = (await request.json()) as {
      type: 'search_results' | 'synthesis_draft' | 'final_digest';
      content: string;
    };

    this.sql.exec(
      `INSERT INTO artifacts (artifact_type, content, created_at) VALUES (?, ?, ?)`,
      body.type,
      body.content,
      new Date().toISOString()
    );

    return new Response(
      JSON.stringify({
        success: true,
      }),
      {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private async completeJob(request: Request): Promise<Response> {
    const body = (await request.json()) as { digestId: string };
    const now = new Date().toISOString();

    this.sql.exec(
      `UPDATE digest_job SET status = 'complete', digest_id = ?, completed_at = ?, updated_at = ?`,
      body.digestId,
      now,
      now
    );

    // Clean up DO storage - workflow complete, results stored elsewhere
    await this.state.storage.deleteAll();
    console.log('[DigestJob] Workflow complete, storage cleared');

    return new Response(
      JSON.stringify({
        success: true,
        data: { digestId: body.digestId },
      }),
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private async failJob(request: Request): Promise<Response> {
    const body = (await request.json()) as { error: string };
    const now = new Date().toISOString();

    this.sql.exec(
      `UPDATE digest_job SET status = 'failed', error_message = ?, updated_at = ?`,
      body.error,
      now
    );

    // Clean up DO storage - workflow failed, no need to keep data
    await this.state.storage.deleteAll();
    console.log('[DigestJob] Workflow failed, storage cleared');

    return new Response(
      JSON.stringify({
        success: false,
        error: {
          code: 'JOB_FAILED',
          message: body.error,
        },
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private async resetJob(): Promise<Response> {
    this.sql.exec('DELETE FROM digest_job');
    this.sql.exec('DELETE FROM articles');
    this.sql.exec('DELETE FROM artifacts');

    return new Response(
      JSON.stringify({
        success: true,
      }),
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  private mapJobRow(row: Record<string, unknown>): DigestJobState {
    return {
      id: row.id as string,
      userId: row.user_id as string,
      status: row.status as JobStatus,
      batchNum: row.batch_num as number,
      articlesFound: row.articles_found as number,
      articlesParsed: row.articles_parsed as number,
      articlesAnalyzed: row.articles_analyzed as number,
      currentTopic: row.current_topic as string | undefined,
      errorMessage: row.error_message as string | undefined,
      startedAt: row.started_at as string,
      updatedAt: row.updated_at as string,
      completedAt: row.completed_at as string | undefined,
      digestId: row.digest_id as string | undefined,
    };
  }
}
