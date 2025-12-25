/**
 * Webhook API Routes.
 *
 * Handles incoming webhooks from external services.
 */

import { Hono } from 'hono';
import type { Env } from '../types';
import { handleDigestComplete } from '../services/orchestrator';
import { deleteServer } from '../services/hetzner';

const webhooks = new Hono<{ Bindings: Env }>();

interface JobStatusPayload {
  job_id: string;
  status?: 'completed' | 'failed' | 'test_completed';
  action?: 'destroy';
  error?: string;
  digest?: {
    markdown: string;
    metadata: {
      topics_covered: string[];
      articles_found: number;
      articles_included: number;
      tokens_used: number;
      cost_usd: number;
    };
  };
}

/**
 * POST /webhooks/digest-complete - Handle digest generation completion.
 *
 * Called by the Python orchestrator when digest generation finishes.
 */
webhooks.post('/digest-complete', async (c) => {
  try {
    // Verify webhook signature if configured
    const webhookSecret = c.env.WEBHOOK_SECRET;
    if (webhookSecret) {
      const signature = c.req.header('X-Webhook-Signature');
      if (!signature) {
        return c.json(
          { success: false, error: { code: 'UNAUTHORIZED', message: 'Missing signature' } },
          401
        );
      }

      // Verify HMAC signature
      const body = await c.req.text();
      const expectedSignature = await computeHmac(body, webhookSecret);

      if (signature !== expectedSignature) {
        return c.json(
          { success: false, error: { code: 'UNAUTHORIZED', message: 'Invalid signature' } },
          401
        );
      }

      // Parse body (we already read it as text for signature verification)
      const payload = JSON.parse(body);
      const result = await handleDigestComplete(c.env, payload);

      if (!result.success) {
        return c.json(
          { success: false, error: { code: 'PROCESSING_ERROR', message: result.error } },
          500
        );
      }

      return c.json({ success: true });
    }

    // No signature verification configured
    const payload = await c.req.json();
    const result = await handleDigestComplete(c.env, payload);

    if (!result.success) {
      return c.json(
        { success: false, error: { code: 'PROCESSING_ERROR', message: result.error } },
        500
      );
    }

    return c.json({ success: true });
  } catch (error) {
    console.error('Webhook error:', error);
    return c.json(
      {
        success: false,
        error: {
          code: 'INTERNAL_ERROR',
          message: error instanceof Error ? error.message : 'Webhook processing failed',
        },
      },
      500
    );
  }
});

/**
 * POST /webhooks/job-status - Receive status updates from ephemeral servers
 *
 * Called by ephemeral Hetzner VPS instances during digest generation lifecycle.
 */
webhooks.post('/job-status', async (c) => {
  const payload: JobStatusPayload = await c.req.json();
  const { job_id, status, action, error, digest } = payload;

  if (!job_id) {
    return c.json(
      { success: false, error: { code: 'INVALID_REQUEST', message: 'job_id is required' } },
      400
    );
  }

  // Get job record
  const job = await c.env.DB.prepare(`
    SELECT * FROM jobs WHERE id = ?
  `).bind(job_id).first();

  if (!job) {
    return c.json(
      { success: false, error: { code: 'NOT_FOUND', message: 'Job not found' } },
      404
    );
  }

  try {
    // Handle destroy action
    if (action === 'destroy') {
      await c.env.DB.prepare(`
        INSERT INTO server_logs (job_id, level, message)
        VALUES (?, 'info', 'Server requesting self-destruct')
      `).bind(job_id).run();

      // Delete the server
      if (job.server_id) {
        try {
          await deleteServer(c.env, String(job.server_id));

          await c.env.DB.prepare(`
            UPDATE jobs
            SET status = 'destroying'
            WHERE id = ?
          `).bind(job_id).run();

          await c.env.DB.prepare(`
            INSERT INTO server_logs (job_id, level, message)
            VALUES (?, 'info', 'Server deleted successfully')
          `).bind(job_id).run();
        } catch (error) {
          console.error('Failed to delete server:', error);
          await c.env.DB.prepare(`
            INSERT INTO server_logs (job_id, level, message, metadata)
            VALUES (?, 'warn', 'Failed to delete server', ?)
          `).bind(job_id, JSON.stringify({ error: String(error) })).run();
        }
      }

      return c.json({ success: true, message: 'Destruction initiated' });
    }

    // Handle status updates
    if (status === 'completed' && digest) {
      // Upload digest to R2
      const r2Key = `digests/${job.user_id}/${job_id}.md`;
      await c.env.DIGESTS.put(r2Key, digest.markdown, {
        customMetadata: {
          userId: String(job.user_id),
          jobId: job_id,
          topicsCovered: digest.metadata.topics_covered.join(','),
          articlesFound: String(digest.metadata.articles_found),
          articlesIncluded: String(digest.metadata.articles_included),
          tokensUsed: String(digest.metadata.tokens_used),
          costUsd: String(digest.metadata.cost_usd),
        },
      });

      // Update job with completion details
      await c.env.DB.prepare(`
        UPDATE jobs
        SET status = 'completed',
            completed_at = ?,
            topics_count = ?,
            articles_found = ?,
            articles_included = ?,
            tokens_used = ?,
            cost_usd = ?,
            digest_r2_key = ?
        WHERE id = ?
      `).bind(
        new Date().toISOString(),
        digest.metadata.topics_covered.length,
        digest.metadata.articles_found,
        digest.metadata.articles_included,
        digest.metadata.tokens_used,
        digest.metadata.cost_usd,
        r2Key,
        job_id
      ).run();

      await c.env.DB.prepare(`
        INSERT INTO server_logs (job_id, level, message, metadata)
        VALUES (?, 'info', 'Digest generated and uploaded', ?)
      `).bind(job_id, JSON.stringify({
        topics: digest.metadata.topics_covered.length,
        articles: digest.metadata.articles_included,
        cost: digest.metadata.cost_usd,
      })).run();

      return c.json({ success: true, message: 'Digest saved successfully' });
    }

    if (status === 'failed') {
      // Update job with error
      await c.env.DB.prepare(`
        UPDATE jobs
        SET status = 'failed',
            error = ?,
            completed_at = ?
        WHERE id = ?
      `).bind(error || 'Unknown error', new Date().toISOString(), job_id).run();

      await c.env.DB.prepare(`
        INSERT INTO server_logs (job_id, level, message, metadata)
        VALUES (?, 'error', 'Digest generation failed', ?)
      `).bind(job_id, JSON.stringify({ error })).run();

      return c.json({ success: true, message: 'Error logged' });
    }

    if (status === 'test_completed') {
      // Test server completed successfully
      await c.env.DB.prepare(`
        UPDATE jobs
        SET status = 'completed',
            completed_at = ?
        WHERE id = ?
      `).bind(new Date().toISOString(), job_id).run();

      await c.env.DB.prepare(`
        INSERT INTO server_logs (job_id, level, message)
        VALUES (?, 'info', 'Test server completed successfully')
      `).bind(job_id).run();

      return c.json({ success: true, message: 'Test completed' });
    }

    // Unknown status
    return c.json(
      { success: false, error: { code: 'INVALID_REQUEST', message: 'Invalid status or action' } },
      400
    );
  } catch (error) {
    console.error('Webhook error:', error);

    await c.env.DB.prepare(`
      INSERT INTO server_logs (job_id, level, message, metadata)
      VALUES (?, 'error', 'Webhook processing failed', ?)
    `).bind(job_id, JSON.stringify({ error: String(error) })).run();

    return c.json(
      {
        success: false,
        error: {
          code: 'WEBHOOK_ERROR',
          message: error instanceof Error ? error.message : 'Unknown error',
        },
      },
      500
    );
  }
});

/**
 * POST /webhooks/resend - Handle Resend email events.
 *
 * Handles delivery notifications, bounces, and complaints.
 */
webhooks.post('/resend', async (c) => {
  try {
    const event = await c.req.json();

    console.log('Resend webhook:', event.type, event.data?.email_id);

    switch (event.type) {
      case 'email.delivered':
        // Email was delivered successfully
        break;

      case 'email.bounced':
        // Handle bounce - might want to mark user email as invalid
        console.warn('Email bounced:', event.data);
        break;

      case 'email.complained':
        // Handle spam complaint - should unsubscribe user
        console.warn('Spam complaint:', event.data);
        break;

      case 'email.opened':
        // Track email opens if needed
        break;

      case 'email.clicked':
        // Track link clicks if needed
        break;
    }

    return c.json({ success: true });
  } catch (error) {
    console.error('Resend webhook error:', error);
    return c.json({ success: false }, 500);
  }
});

/**
 * Compute HMAC-SHA256 signature.
 */
async function computeHmac(payload: string, secret: string): Promise<string> {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signature = await crypto.subtle.sign('HMAC', key, encoder.encode(payload));

  return Array.from(new Uint8Array(signature))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

export { webhooks };
