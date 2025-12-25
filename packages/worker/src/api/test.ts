/**
 * Test API Routes (Development only).
 *
 * Simple endpoints for testing without authentication.
 */

import { Hono } from 'hono';
import type { Env } from '../types';
import { createUser } from '../services/database';

const test = new Hono<{ Bindings: Env }>();

/**
 * POST /test/create-user - Create a test user quickly.
 */
test.post('/create-user', async (c) => {
  const email = `test-${Date.now()}@example.com`;

  try {
    const user = await createUser(c.env.DB, {
      email,
      subscriptionTier: 'free',
      preferences: {
        topics: [
          {
            name: 'AI & Machine Learning',
            keywords: ['AI', 'machine learning', 'LLM'],
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
          timezone: 'America/New_York',
        },
        style: {
          tone: 'hn-style',
          skepticismLevel: 4,
          technicalDepth: 4,
          includeBiasAnalysis: false,
          includeCrossConnections: false,
          maxArticlesPerTopic: 5,
        },
        thresholds: {
          minRelevanceScore: 0.5,
          minQualityScore: 0.5,
          minNoveltyScore: 0.3,
          maxBiasScore: 0.8,
        },
      },
    });

    return c.json({
      success: true,
      data: {
        userId: user.id,
        email: user.email,
        message: 'Test user created successfully',
      },
    });
  } catch (error) {
    console.error('Create test user error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to create test user' },
      },
      500
    );
  }
});

/**
 * GET /test/db - Test database connection.
 */
test.get('/db', async (c) => {
  try {
    const result = await c.env.DB.prepare('SELECT 1 as test').first();
    return c.json({
      success: true,
      data: { database: 'connected', result },
    });
  } catch (error) {
    return c.json(
      {
        success: false,
        error: { code: 'DB_ERROR', message: String(error) },
      },
      500
    );
  }
});

/**
 * GET /test/env - Check environment configuration.
 */
test.get('/env', async (c) => {
  return c.json({
    success: true,
    data: {
      environment: c.env.ENVIRONMENT,
      hasOrchestratorUrl: !!c.env.ORCHESTRATOR_API_URL,
      hasOrchestratorKey: !!c.env.ORCHESTRATOR_API_KEY,
      hasOpenRouter: !!c.env.OPENROUTER_API_KEY,
      hasAnthropic: !!c.env.ANTHROPIC_API_KEY,
      hasTavily: !!c.env.TAVILY_API_KEY,
    },
  });
});

export default test;
