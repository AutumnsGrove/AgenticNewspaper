/**
 * Users API Routes.
 *
 * Handles user preferences, settings, and account management.
 */

import { Hono } from 'hono';
import { z } from 'zod';
import type { Env, UserPreferences } from '../types';
import {
  getUserById,
  updateUserPreferences,
  updateUserTier,
  generateRssToken,
  deleteUser,
  getUserUsageHistory,
} from '../services/database';

const users = new Hono<{ Bindings: Env; Variables: { userId: string } }>();

// ============================================================================
// Validation Schemas
// ============================================================================

const topicSchema = z.object({
  name: z.string().min(1).max(100),
  keywords: z.array(z.string().max(50)).max(20),
  priority: z.number().min(1).max(5),
  enabled: z.boolean(),
});

const sourceSchema = z.object({
  domain: z.string(),
  trust: z.number().min(0).max(1),
  priority: z.number().min(1).max(5),
});

const deliverySchema = z.object({
  frequency: z.enum(['hourly', 'daily_am', 'daily_pm', 'weekly', 'biweekly', 'monthly']),
  deliveryTimeUtc: z.string().regex(/^\d{2}:\d{2}$/),
  channels: z.array(z.enum(['web', 'rss', 'email'])),
  lookbackHours: z.number().min(1).max(720),
  timezone: z.string(),
});

const styleSchema = z.object({
  tone: z.enum(['hn-style', 'formal', 'casual']),
  skepticismLevel: z.number().min(1).max(5),
  technicalDepth: z.number().min(1).max(5),
  includeBiasAnalysis: z.boolean(),
  includeCrossConnections: z.boolean(),
  maxArticlesPerTopic: z.number().min(1).max(20),
});

const thresholdsSchema = z.object({
  minRelevanceScore: z.number().min(0).max(1),
  minQualityScore: z.number().min(0).max(1),
  minNoveltyScore: z.number().min(0).max(1),
  maxBiasScore: z.number().min(0).max(1),
});

const preferencesSchema = z.object({
  topics: z.array(topicSchema).max(50),
  sources: z.array(sourceSchema).max(100),
  delivery: deliverySchema,
  style: styleSchema,
  thresholds: thresholdsSchema,
});

// ============================================================================
// Routes
// ============================================================================

/**
 * GET /users/me - Get current user profile.
 */
users.get('/me', async (c) => {
  const userId = c.get('userId');

  try {
    const user = await getUserById(c.env.DB, userId);
    if (!user) {
      return c.json(
        {
          success: false,
          error: { code: 'NOT_FOUND', message: 'User not found' },
        },
        404
      );
    }

    return c.json({
      success: true,
      data: {
        id: user.id,
        email: user.email,
        subscriptionTier: user.subscriptionTier,
        createdAt: user.createdAt,
        hasRssToken: !!user.rssToken,
      },
    });
  } catch (error) {
    console.error('Get user error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to get user' },
      },
      500
    );
  }
});

/**
 * GET /users/me/preferences - Get user preferences.
 */
users.get('/me/preferences', async (c) => {
  const userId = c.get('userId');

  try {
    // Get from Durable Object for most up-to-date preferences
    const doId = c.env.USER_STATE.idFromName(userId);
    const stub = c.env.USER_STATE.get(doId);

    const response = await stub.fetch(new Request('https://do/preferences'));
    const result = (await response.json()) as { success: boolean; data: UserPreferences };

    return c.json(result);
  } catch (error) {
    console.error('Get preferences error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to get preferences' },
      },
      500
    );
  }
});

/**
 * PUT /users/me/preferences - Update user preferences.
 */
users.put('/me/preferences', async (c) => {
  const userId = c.get('userId');

  try {
    const body = await c.req.json();
    const parsed = preferencesSchema.safeParse(body);

    if (!parsed.success) {
      return c.json(
        {
          success: false,
          error: { code: 'VALIDATION_ERROR', message: parsed.error.message },
        },
        400
      );
    }

    const preferences = parsed.data as UserPreferences;

    // Update in D1
    await updateUserPreferences(c.env.DB, userId, preferences);

    // Update in Durable Object
    const doId = c.env.USER_STATE.idFromName(userId);
    const stub = c.env.USER_STATE.get(doId);

    await stub.fetch(
      new Request('https://do/preferences', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences),
      })
    );

    return c.json({
      success: true,
      data: preferences,
    });
  } catch (error) {
    console.error('Update preferences error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to update preferences' },
      },
      500
    );
  }
});

/**
 * PATCH /users/me/preferences/topics - Update topics only.
 */
users.patch('/me/preferences/topics', async (c) => {
  const userId = c.get('userId');

  try {
    const body = await c.req.json();
    const parsed = z.array(topicSchema).safeParse(body);

    if (!parsed.success) {
      return c.json(
        {
          success: false,
          error: { code: 'VALIDATION_ERROR', message: parsed.error.message },
        },
        400
      );
    }

    // Get current preferences
    const user = await getUserById(c.env.DB, userId);
    if (!user) {
      return c.json(
        {
          success: false,
          error: { code: 'NOT_FOUND', message: 'User not found' },
        },
        404
      );
    }

    const updatedPreferences = {
      ...user.preferences,
      topics: parsed.data,
    };

    await updateUserPreferences(c.env.DB, userId, updatedPreferences);

    return c.json({
      success: true,
      data: { topics: parsed.data },
    });
  } catch (error) {
    console.error('Update topics error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to update topics' },
      },
      500
    );
  }
});

/**
 * POST /users/me/rss-token - Generate new RSS token.
 */
users.post('/me/rss-token', async (c) => {
  const userId = c.get('userId');

  try {
    const token = await generateRssToken(c.env.DB, userId);

    return c.json({
      success: true,
      data: {
        token,
        feedUrl: `https://clearing.autumnsgrove.com/rss/${userId}/${token}`,
      },
    });
  } catch (error) {
    console.error('Generate RSS token error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to generate RSS token' },
      },
      500
    );
  }
});

/**
 * GET /users/me/usage - Get usage statistics.
 */
users.get('/me/usage', async (c) => {
  const userId = c.get('userId');
  const months = parseInt(c.req.query('months') || '6', 10);

  try {
    const history = await getUserUsageHistory(c.env.DB, userId, months);

    // Get stats from Durable Object
    const doId = c.env.USER_STATE.idFromName(userId);
    const stub = c.env.USER_STATE.get(doId);

    const statsResponse = await stub.fetch(new Request('https://do/stats'));
    const statsResult = (await statsResponse.json()) as { success: boolean; data: Record<string, unknown> };

    return c.json({
      success: true,
      data: {
        history,
        summary: statsResult.data,
      },
    });
  } catch (error) {
    console.error('Get usage error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to get usage' },
      },
      500
    );
  }
});

/**
 * GET /users/me/weights - Get learned preference weights.
 */
users.get('/me/weights', async (c) => {
  const userId = c.get('userId');

  try {
    const doId = c.env.USER_STATE.idFromName(userId);
    const stub = c.env.USER_STATE.get(doId);

    const response = await stub.fetch(new Request('https://do/weights'));
    const result = await response.json();

    return c.json(result);
  } catch (error) {
    console.error('Get weights error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to get weights' },
      },
      500
    );
  }
});

/**
 * DELETE /users/me - Delete user account.
 */
users.delete('/me', async (c) => {
  const userId = c.get('userId');

  try {
    // Delete from D1
    await deleteUser(c.env.DB, userId);

    // Clear Durable Object state
    const digestJobId = c.env.DIGEST_JOB.idFromName(userId);
    const digestJobStub = c.env.DIGEST_JOB.get(digestJobId);
    await digestJobStub.fetch(new Request('https://do/reset', { method: 'DELETE' }));

    const userStateId = c.env.USER_STATE.idFromName(userId);
    const userStateStub = c.env.USER_STATE.get(userStateId);
    await userStateStub.fetch(new Request('https://do/history', { method: 'DELETE' }));

    return c.json({
      success: true,
      message: 'Account deleted successfully',
    });
  } catch (error) {
    console.error('Delete user error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to delete account' },
      },
      500
    );
  }
});

export { users };
