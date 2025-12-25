/**
 * Webhook API Routes.
 *
 * Handles incoming webhooks from external services.
 */

import { Hono } from 'hono';
import type { Env } from '../types';
import { handleDigestComplete } from '../services/orchestrator';

const webhooks = new Hono<{ Bindings: Env }>();

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
