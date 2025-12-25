/**
 * The Daily Clearing - Cloudflare Worker Entry Point.
 *
 * Main worker that handles API requests, Durable Object bindings,
 * and scheduled digest generation.
 */

import { Hono } from 'hono';
import type { Env } from './types';
import { auth, digests, users, rss, webhooks, test } from './api';
import { DigestJob, UserState, startDigestGeneration } from './services';
import {
  cors,
  rateLimit,
  authenticate,
  logger,
  errorHandler,
  securityHeaders,
} from './utils/middleware';

// ============================================================================
// Main App
// ============================================================================

const app = new Hono<{ Bindings: Env }>();

// Global middleware
app.use('*', logger());
app.use('*', errorHandler());
app.use('*', cors());
app.use('*', securityHeaders());

// Rate limiting for API routes
app.use('/api/*', rateLimit({ windowMs: 60000, maxRequests: 100 }));

// ============================================================================
// Health & Info Routes
// ============================================================================

app.get('/', (c) => {
  return c.json({
    name: 'The Daily Clearing',
    version: '1.0.0',
    status: 'operational',
    documentation: 'https://clearing.autumnsgrove.com/docs',
  });
});

app.get('/health', (c) => {
  return c.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    environment: c.env.ENVIRONMENT,
  });
});

// ============================================================================
// Public Routes
// ============================================================================

// Authentication (no auth required)
app.route('/api/auth', auth);

// RSS feeds (token-based auth)
app.route('/rss', rss);

// Webhooks (signature-verified)
app.route('/api/webhooks', webhooks);

// Test routes (development only)
if (process.env.ENVIRONMENT !== 'production') {
  app.route('/api/test', test);
}

// ============================================================================
// Protected Routes
// ============================================================================

// Apply authentication middleware to protected routes
app.use('/api/users/*', authenticate());
app.use('/api/digests/*', authenticate());

// User management
app.route('/api/users', users);

// Digest management
app.route('/api/digests', digests);

// ============================================================================
// Fallback
// ============================================================================

app.notFound((c) => {
  return c.json(
    {
      success: false,
      error: { code: 'NOT_FOUND', message: 'Route not found' },
    },
    404
  );
});

// ============================================================================
// Scheduled Handlers
// ============================================================================

interface ScheduledEvent {
  cron: string;
  type: string;
  scheduledTime: number;
}

async function handleScheduled(event: ScheduledEvent, env: Env, _ctx: ExecutionContext): Promise<void> {
  console.log(`Scheduled event: ${event.cron} at ${new Date(event.scheduledTime).toISOString()}`);

  // Different cron patterns for different tasks
  switch (event.cron) {
    case '0 6 * * *': // 6 AM UTC daily
      await triggerDailyDigests(env, 'daily_am');
      break;

    case '0 18 * * *': // 6 PM UTC daily
      await triggerDailyDigests(env, 'daily_pm');
      break;

    case '0 6 * * 1': // 6 AM UTC Mondays
      await triggerWeeklyDigests(env);
      break;

    case '0 * * * *': // Every hour
      await triggerHourlyDigests(env);
      break;

    case '0 0 * * *': // Midnight UTC
      await cleanupOldData(env);
      break;

    default:
      console.log(`Unknown cron pattern: ${event.cron}`);
  }
}

/**
 * Trigger daily digest generation for subscribed users.
 */
async function triggerDailyDigests(env: Env, frequency: string): Promise<void> {
  try {
    const result = await env.DB.prepare(
      `SELECT id, preferences_json FROM users
       WHERE json_extract(preferences_json, '$.deliveryFrequency') = 'daily'
       AND json_extract(preferences_json, '$.channels') LIKE '%"email"%'`
    ).all();

    console.log(`Triggering ${result.results.length} ${frequency} digests`);

    for (const row of result.results) {
      const userId = row.id as string;
      const preferencesJson = row.preferences_json as string;

      // Parse user preferences
      let preferences;
      try {
        preferences = JSON.parse(preferencesJson || '{}');
      } catch {
        console.error(`Invalid preferences for user ${userId}`);
        continue;
      }

      // Track job in Durable Object
      const doId = env.DIGEST_JOB.idFromName(userId);
      const stub = env.DIGEST_JOB.get(doId);
      const jobId = `${userId}_${Date.now()}`;

      await stub.fetch(
        new Request('https://do/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ userId, jobId }),
        })
      );

      // Start orchestrator generation (async, will callback via webhook)
      const orchestratorResult = await startDigestGeneration(env, userId, preferences);

      if (!orchestratorResult.success) {
        console.error(`Failed to start digest for ${userId}:`, orchestratorResult.error);
        await stub.fetch(
          new Request('https://do/fail', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ error: orchestratorResult.error }),
          })
        );
      }
    }
  } catch (error) {
    console.error('Error triggering daily digests:', error);
  }
}

/**
 * Trigger weekly digest generation.
 */
async function triggerWeeklyDigests(env: Env): Promise<void> {
  try {
    const result = await env.DB.prepare(
      `SELECT id, preferences_json FROM users
       WHERE json_extract(preferences_json, '$.deliveryFrequency') IN ('weekly', 'biweekly')`
    ).all();

    console.log(`Triggering ${result.results.length} weekly digests`);

    for (const row of result.results) {
      const userId = row.id as string;
      const preferencesJson = row.preferences_json as string;

      let preferences;
      try {
        preferences = JSON.parse(preferencesJson || '{}');
      } catch {
        continue;
      }

      const doId = env.DIGEST_JOB.idFromName(userId);
      const stub = env.DIGEST_JOB.get(doId);
      const jobId = `${userId}_${Date.now()}`;

      await stub.fetch(
        new Request('https://do/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ userId, jobId }),
        })
      );

      const orchestratorResult = await startDigestGeneration(env, userId, preferences);
      if (!orchestratorResult.success) {
        await stub.fetch(
          new Request('https://do/fail', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ error: orchestratorResult.error }),
          })
        );
      }
    }
  } catch (error) {
    console.error('Error triggering weekly digests:', error);
  }
}

/**
 * Trigger hourly digest generation.
 */
async function triggerHourlyDigests(env: Env): Promise<void> {
  try {
    const result = await env.DB.prepare(
      `SELECT id, preferences_json FROM users
       WHERE json_extract(preferences_json, '$.deliveryFrequency') = 'hourly'`
    ).all();

    console.log(`Triggering ${result.results.length} hourly digests`);

    for (const row of result.results) {
      const userId = row.id as string;
      const preferencesJson = row.preferences_json as string;

      let preferences;
      try {
        preferences = JSON.parse(preferencesJson || '{}');
      } catch {
        continue;
      }

      const doId = env.DIGEST_JOB.idFromName(userId);
      const stub = env.DIGEST_JOB.get(doId);
      const jobId = `${userId}_${Date.now()}`;

      await stub.fetch(
        new Request('https://do/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ userId, jobId }),
        })
      );

      const orchestratorResult = await startDigestGeneration(env, userId, preferences);
      if (!orchestratorResult.success) {
        await stub.fetch(
          new Request('https://do/fail', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ error: orchestratorResult.error }),
          })
        );
      }
    }
  } catch (error) {
    console.error('Error triggering hourly digests:', error);
  }
}

/**
 * Cleanup old data and expired cache.
 */
async function cleanupOldData(env: Env): Promise<void> {
  try {
    // Clean up old cache entries
    const { cleanupExpiredCache } = await import('./services/storage');
    const result = await cleanupExpiredCache(env);
    console.log(`Cleaned up ${result.deleted} expired cache entries`);

    // Clean up old feedback (older than 90 days)
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - 90);

    await env.DB.prepare('DELETE FROM feedback WHERE created_at < ?')
      .bind(cutoffDate.toISOString())
      .run();

    console.log('Cleanup completed');
  } catch (error) {
    console.error('Error during cleanup:', error);
  }
}

// ============================================================================
// Exports
// ============================================================================

export default {
  fetch: app.fetch,
  scheduled: handleScheduled,
};

// Export Durable Objects
export { DigestJob, UserState };
