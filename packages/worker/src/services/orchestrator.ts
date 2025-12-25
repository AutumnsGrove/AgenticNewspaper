/**
 * Orchestrator Service.
 *
 * Bridges the Cloudflare Worker with the Python orchestrator API.
 * Handles digest generation requests and progress tracking.
 */

import type { Env, UserPreferences, Digest } from '../types';
import { storeDigest } from './storage';
import { sendDigestEmail, sendDigestNotificationEmail } from './email';
import { getUserById } from './database';

// DigestGenerationRequest: Used for type reference (JSON body sent to Python API)
// interface DigestGenerationRequest {
//   userId: string;
//   jobId: string;
//   preferences: UserPreferences;
//   webhookUrl?: string;
// }

interface DigestProgress {
  jobId: string;
  status: string;
  progress: number;
  currentStep: string;
  articlesFound: number;
  articlesParsed: number;
  articlesIncluded: number;
  error?: string;
}

interface DigestResult {
  jobId: string;
  success: boolean;
  digestId?: string;
  markdown?: string;
  metadata?: {
    digestId: string;
    generatedAt: string;
    topicsCovered: string[];
    totalArticlesFound: number;
    totalArticlesParsed: number;
    totalArticlesIncluded: number;
    totalTokensUsed: number;
    totalCostUsd: number;
  };
  error?: string;
}

/**
 * Start digest generation via the Python orchestrator API.
 */
export async function startDigestGeneration(
  env: Env,
  userId: string,
  preferences: UserPreferences
): Promise<{ success: boolean; jobId?: string; error?: string }> {
  const orchestratorUrl = env.ORCHESTRATOR_API_URL;

  if (!orchestratorUrl) {
    return { success: false, error: 'ORCHESTRATOR_API_URL not configured' };
  }

  const jobId = `${userId}_${Date.now()}`;
  const webhookUrl = env.WORKER_URL ? `${env.WORKER_URL}/api/webhooks/digest-complete` : undefined;

  try {
    const response = await fetch(`${orchestratorUrl}/api/digest/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${env.ORCHESTRATOR_API_KEY || ''}`,
      },
      body: JSON.stringify({
        user_id: userId,
        job_id: jobId,
        preferences: convertPreferences(preferences),
        webhook_url: webhookUrl,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      return { success: false, error: `Orchestrator API error: ${error}` };
    }

    const result = (await response.json()) as { success: boolean; job_id: string };
    return { success: true, jobId: result.job_id };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to start digest generation',
    };
  }
}

/**
 * Get progress of digest generation.
 */
export async function getDigestProgress(
  env: Env,
  jobId: string
): Promise<DigestProgress | null> {
  const orchestratorUrl = env.ORCHESTRATOR_API_URL;

  if (!orchestratorUrl) {
    return null;
  }

  try {
    const response = await fetch(`${orchestratorUrl}/api/digest/${jobId}/progress`, {
      headers: {
        Authorization: `Bearer ${env.ORCHESTRATOR_API_KEY || ''}`,
      },
    });

    if (!response.ok) {
      return null;
    }

    const data = (await response.json()) as {
      job_id: string;
      status: string;
      progress: number;
      current_step: string;
      articles_found: number;
      articles_parsed: number;
      articles_included: number;
      error?: string;
    };

    return {
      jobId: data.job_id,
      status: data.status,
      progress: data.progress,
      currentStep: data.current_step,
      articlesFound: data.articles_found,
      articlesParsed: data.articles_parsed,
      articlesIncluded: data.articles_included,
      error: data.error,
    };
  } catch {
    return null;
  }
}

/**
 * Get result of completed digest generation.
 */
export async function getDigestResult(
  env: Env,
  jobId: string
): Promise<DigestResult | null> {
  const orchestratorUrl = env.ORCHESTRATOR_API_URL;

  if (!orchestratorUrl) {
    return null;
  }

  try {
    const response = await fetch(`${orchestratorUrl}/api/digest/${jobId}/result`, {
      headers: {
        Authorization: `Bearer ${env.ORCHESTRATOR_API_KEY || ''}`,
      },
    });

    if (!response.ok) {
      return null;
    }

    const data = (await response.json()) as {
      job_id: string;
      success: boolean;
      digest_id?: string;
      markdown?: string;
      metadata?: {
        digest_id: string;
        generated_at: string;
        topics_covered: string[];
        total_articles_found: number;
        total_articles_parsed: number;
        total_articles_included: number;
        total_tokens_used: number;
        total_cost_usd: number;
      };
      error?: string;
    };

    return {
      jobId: data.job_id,
      success: data.success,
      digestId: data.digest_id,
      markdown: data.markdown,
      metadata: data.metadata
        ? {
            digestId: data.metadata.digest_id,
            generatedAt: data.metadata.generated_at,
            topicsCovered: data.metadata.topics_covered,
            totalArticlesFound: data.metadata.total_articles_found,
            totalArticlesParsed: data.metadata.total_articles_parsed,
            totalArticlesIncluded: data.metadata.total_articles_included,
            totalTokensUsed: data.metadata.total_tokens_used,
            totalCostUsd: data.metadata.total_cost_usd,
          }
        : undefined,
      error: data.error,
    };
  } catch {
    return null;
  }
}

/**
 * Handle webhook callback when digest generation completes.
 */
export async function handleDigestComplete(
  env: Env,
  payload: {
    job_id: string;
    status: string;
    result?: {
      digest_id: string;
      markdown: string;
      metadata: Record<string, unknown>;
    };
    error?: string;
  }
): Promise<{ success: boolean; error?: string }> {
  const jobId = payload.job_id;
  const userId = jobId.split('_')[0]; // Extract userId from jobId

  if (payload.status === 'failed') {
    console.error(`Digest generation failed for ${userId}:`, payload.error);
    return { success: false, error: payload.error };
  }

  if (payload.status !== 'complete' || !payload.result) {
    return { success: false, error: 'Invalid webhook payload' };
  }

  try {
    const { digest_id, markdown, metadata } = payload.result;

    // Build digest object for storage
    const digest: Digest = {
      metadata: {
        digestId: digest_id,
        generatedAt: new Date().toISOString(),
        topicsCovered: (metadata.topics_covered as string[]) || [],
        totalArticlesFound: (metadata.total_articles_found as number) || 0,
        totalArticlesParsed: (metadata.total_articles_parsed as number) || 0,
        totalArticlesIncluded: (metadata.total_articles_included as number) || 0,
        totalTokensUsed: (metadata.total_tokens_used as number) || 0,
        totalCostUsd: (metadata.total_cost_usd as number) || 0,
        processingTimeSeconds: 0,
      },
      sections: [], // Will be parsed from markdown if needed
      // Note: markdown stored separately in R2, not in digest object
    };

    // Store digest in R2
    await storeDigest(env, userId, digest_id, digest, markdown);

    // Get user for email delivery
    const user = await getUserById(env.DB, userId);
    if (!user) {
      return { success: true }; // Digest stored, but user not found for email
    }

    // Send email notification if user has email channel enabled
    const prefs = user.preferences;
    if (prefs?.delivery?.channels?.includes('email')) {
      const webUrl = env.WEB_URL || 'https://clearing.autumnsgrove.com';

      // Send digest notification (full email format not yet implemented)
      const sendFullDigest = false; // TODO: Add emailFormat to preferences
      if (sendFullDigest) {
        await sendDigestEmail(env, {
          to: user.email,
          userId: user.id,
          digestId: digest_id,
          digest,
          unsubscribeUrl: `${webUrl}/unsubscribe?user=${user.id}`,
          webUrl,
        });
      } else {
        await sendDigestNotificationEmail(env, {
          to: user.email,
          userId: user.id,
          digestId: digest_id,
          articleCount: digest.metadata.totalArticlesIncluded,
          topicCount: digest.metadata.topicsCovered.length,
          webUrl,
        });
      }
    }

    return { success: true };
  } catch (error) {
    console.error('Error handling digest complete webhook:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to process digest',
    };
  }
}

/**
 * Poll for digest completion (alternative to webhooks).
 */
export async function pollForCompletion(
  env: Env,
  jobId: string,
  maxWaitMs: number = 300000, // 5 minutes
  pollIntervalMs: number = 5000
): Promise<DigestResult | null> {
  const startTime = Date.now();

  while (Date.now() - startTime < maxWaitMs) {
    const progress = await getDigestProgress(env, jobId);

    if (!progress) {
      return null;
    }

    if (progress.status === 'complete' || progress.status === 'failed') {
      return await getDigestResult(env, jobId);
    }

    // Wait before next poll
    await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
  }

  return null; // Timeout
}

/**
 * Convert frontend preferences to orchestrator format.
 */
function convertPreferences(prefs: UserPreferences): Record<string, unknown> {
  return {
    topics: prefs.topics.map((t) => ({
      name: t.name,
      keywords: t.keywords,
      priority: t.priority,
      enabled: t.enabled,
      max_articles: 5,
    })),
    sources: {
      tier1_premium: [], // Could populate from user settings
    },
    digest_settings: {
      tone: prefs.style.tone,
      skepticism_level: prefs.style.skepticismLevel,
      technical_depth: prefs.style.technicalDepth,
      include_bias_analysis: prefs.style.includeBiasAnalysis,
      include_cross_connections: prefs.style.includeCrossConnections,
    },
    delivery: {
      frequency: prefs.delivery.frequency,
      time: prefs.delivery.deliveryTimeUtc,
      channels: prefs.delivery.channels,
    },
    budget: {
      daily_target_usd: 0.3,
      abort_threshold_usd: 0.5,
    },
    advanced: {
      max_parallel_parsers: 5,
    },
  };
}
