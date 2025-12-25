/**
 * Digests API Routes.
 *
 * Handles digest generation, retrieval, and management.
 */

import { Hono } from 'hono';
import { z } from 'zod';
import type { Env, DigestJobProgress, Digest } from '../types';
import {
  listUserDigestRecords,
  getDigestRecord,
  createFeedback,
  incrementUsage,
} from '../services/database';
import { getDigest, listUserDigests, storeDigest } from '../services/storage';

const digests = new Hono<{ Bindings: Env; Variables: { userId: string } }>();

// ============================================================================
// Validation Schemas
// ============================================================================

const generateOptionsSchema = z.object({
  topics: z.array(z.string()).optional(),
  lookbackHours: z.number().min(1).max(720).optional(),
  maxArticles: z.number().min(1).max(100).optional(),
});

const feedbackSchema = z.object({
  articleUrl: z.string().url().optional(),
  type: z.enum(['like', 'dislike', 'read', 'skip', 'share', 'save']),
  notes: z.string().max(500).optional(),
});

// ============================================================================
// Routes
// ============================================================================

/**
 * GET /digests - List user's digests.
 */
digests.get('/', async (c) => {
  const userId = c.get('userId');
  const page = parseInt(c.req.query('page') || '1', 10);
  const pageSize = parseInt(c.req.query('pageSize') || '20', 10);
  const offset = (page - 1) * pageSize;

  try {
    const { records, total } = await listUserDigestRecords(c.env.DB, userId, {
      limit: pageSize,
      offset,
    });

    return c.json({
      success: true,
      data: records,
      pagination: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize),
        hasNext: offset + pageSize < total,
        hasPrev: page > 1,
      },
    });
  } catch (error) {
    console.error('List digests error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to list digests' },
      },
      500
    );
  }
});

/**
 * GET /digests/:id - Get a specific digest.
 */
digests.get('/:id', async (c) => {
  const userId = c.get('userId');
  const digestId = c.req.param('id');

  try {
    // Get record from D1
    const record = await getDigestRecord(c.env.DB, digestId);
    if (!record || record.userId !== userId) {
      return c.json(
        {
          success: false,
          error: { code: 'NOT_FOUND', message: 'Digest not found' },
        },
        404
      );
    }

    // Get full digest from R2
    const stored = await getDigest(c.env, userId, digestId);
    if (!stored) {
      return c.json(
        {
          success: false,
          error: { code: 'NOT_FOUND', message: 'Digest content not found' },
        },
        404
      );
    }

    return c.json({
      success: true,
      data: {
        ...stored.digest,
        markdown: stored.markdown,
        html: stored.html,
      },
    });
  } catch (error) {
    console.error('Get digest error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to get digest' },
      },
      500
    );
  }
});

/**
 * POST /digests/generate - Start digest generation.
 */
digests.post('/generate', async (c) => {
  const userId = c.get('userId');

  try {
    const body = await c.req.json().catch(() => ({}));
    const parsed = generateOptionsSchema.safeParse(body);

    if (!parsed.success) {
      return c.json(
        {
          success: false,
          error: { code: 'VALIDATION_ERROR', message: parsed.error.message },
        },
        400
      );
    }

    // Get user's Durable Object
    const doId = c.env.DIGEST_JOB.idFromName(userId);
    const stub = c.env.DIGEST_JOB.get(doId);

    // Check if a job is already running
    const statusResponse = await stub.fetch(new Request('https://do/status'));
    const statusResult = (await statusResponse.json()) as { success: boolean; data: { status: string } | null };

    if (statusResult.data && !['complete', 'failed'].includes(statusResult.data.status)) {
      return c.json(
        {
          success: false,
          error: { code: 'JOB_IN_PROGRESS', message: 'A digest generation is already in progress' },
        },
        409
      );
    }

    // Start new job
    const jobId = `${userId}_${Date.now()}`;
    const startResponse = await stub.fetch(
      new Request('https://do/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId, jobId }),
      })
    );

    if (!startResponse.ok) {
      throw new Error('Failed to start digest job');
    }

    // Update usage
    const month = new Date().toISOString().slice(0, 7);
    await incrementUsage(c.env.DB, userId, month, { digestCount: 1 });

    return c.json({
      success: true,
      data: {
        jobId,
        status: 'pending',
        message: 'Digest generation started',
      },
    });
  } catch (error) {
    console.error('Generate digest error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to start digest generation' },
      },
      500
    );
  }
});

/**
 * GET /digests/generate/status - Get generation progress.
 */
digests.get('/generate/status', async (c) => {
  const userId = c.get('userId');

  try {
    const doId = c.env.DIGEST_JOB.idFromName(userId);
    const stub = c.env.DIGEST_JOB.get(doId);

    const response = await stub.fetch(new Request('https://do/progress'));
    const result = (await response.json()) as { success: boolean; data: DigestJobProgress };

    return c.json(result);
  } catch (error) {
    console.error('Get status error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to get generation status' },
      },
      500
    );
  }
});

/**
 * DELETE /digests/generate - Cancel generation.
 */
digests.delete('/generate', async (c) => {
  const userId = c.get('userId');

  try {
    const doId = c.env.DIGEST_JOB.idFromName(userId);
    const stub = c.env.DIGEST_JOB.get(doId);

    await stub.fetch(new Request('https://do/reset', { method: 'DELETE' }));

    return c.json({
      success: true,
      message: 'Digest generation cancelled',
    });
  } catch (error) {
    console.error('Cancel generation error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to cancel generation' },
      },
      500
    );
  }
});

/**
 * POST /digests/:id/feedback - Submit feedback for a digest.
 */
digests.post('/:id/feedback', async (c) => {
  const userId = c.get('userId');
  const digestId = c.req.param('id');

  try {
    const body = await c.req.json();
    const parsed = feedbackSchema.safeParse(body);

    if (!parsed.success) {
      return c.json(
        {
          success: false,
          error: { code: 'VALIDATION_ERROR', message: parsed.error.message },
        },
        400
      );
    }

    // Verify digest exists and belongs to user
    const record = await getDigestRecord(c.env.DB, digestId);
    if (!record || record.userId !== userId) {
      return c.json(
        {
          success: false,
          error: { code: 'NOT_FOUND', message: 'Digest not found' },
        },
        404
      );
    }

    // Create feedback
    const feedback = await createFeedback(c.env.DB, {
      id: crypto.randomUUID(),
      userId,
      digestId,
      articleUrl: parsed.data.articleUrl,
      type: parsed.data.type,
    });

    // Also record in Durable Object for learning
    const userStateId = c.env.USER_STATE.idFromName(userId);
    const userStateStub = c.env.USER_STATE.get(userStateId);

    await userStateStub.fetch(
      new Request('https://do/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: feedback.id,
          digestId,
          articleUrl: parsed.data.articleUrl,
          type: parsed.data.type,
          notes: parsed.data.notes,
        }),
      })
    );

    return c.json({
      success: true,
      data: feedback,
    });
  } catch (error) {
    console.error('Submit feedback error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to submit feedback' },
      },
      500
    );
  }
});

/**
 * GET /digests/latest - Get the most recent digest.
 */
digests.get('/latest', async (c) => {
  const userId = c.get('userId');

  try {
    const { records } = await listUserDigestRecords(c.env.DB, userId, { limit: 1 });

    if (records.length === 0) {
      return c.json(
        {
          success: false,
          error: { code: 'NOT_FOUND', message: 'No digests found' },
        },
        404
      );
    }

    const record = records[0];
    const stored = await getDigest(c.env, userId, record.id);

    if (!stored) {
      return c.json(
        {
          success: false,
          error: { code: 'NOT_FOUND', message: 'Digest content not found' },
        },
        404
      );
    }

    return c.json({
      success: true,
      data: {
        ...stored.digest,
        markdown: stored.markdown,
      },
    });
  } catch (error) {
    console.error('Get latest digest error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to get latest digest' },
      },
      500
    );
  }
});

export { digests };
