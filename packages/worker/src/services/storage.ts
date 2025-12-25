/**
 * R2 Storage Service.
 *
 * Handles digest storage and caching in Cloudflare R2.
 */

import type { Env, Digest } from '../types';

export interface StoredDigest {
  digest: Digest;
  markdown: string;
  html?: string;
  createdAt: string;
  expiresAt?: string;
}

export interface CacheEntry<T> {
  data: T;
  createdAt: string;
  expiresAt: string;
}

/**
 * Generate R2 key for user digest.
 */
export function getDigestKey(userId: string, digestId: string): string {
  // Organize by user and date
  const datePart = digestId.split('_')[0] || digestId;
  return `users/${userId}/digests/${datePart}/${digestId}.json`;
}

/**
 * Generate R2 key for cache entry.
 */
export function getCacheKey(type: string, identifier: string): string {
  return `cache/${type}/${identifier}.json`;
}

/**
 * Store a digest in R2.
 */
export async function storeDigest(
  env: Env,
  userId: string,
  digestId: string,
  digest: Digest,
  markdown: string,
  html?: string
): Promise<string> {
  const key = getDigestKey(userId, digestId);

  const stored: StoredDigest = {
    digest,
    markdown,
    html,
    createdAt: new Date().toISOString(),
  };

  await env.DIGESTS.put(key, JSON.stringify(stored), {
    customMetadata: {
      userId,
      digestId,
      topicCount: String(digest.sections.length),
      articleCount: String(digest.metadata.totalArticlesIncluded),
    },
  });

  return key;
}

/**
 * Retrieve a digest from R2.
 */
export async function getDigest(
  env: Env,
  userId: string,
  digestId: string
): Promise<StoredDigest | null> {
  const key = getDigestKey(userId, digestId);
  const object = await env.DIGESTS.get(key);

  if (!object) {
    return null;
  }

  const text = await object.text();
  return JSON.parse(text) as StoredDigest;
}

/**
 * List user's digests with pagination.
 */
export async function listUserDigests(
  env: Env,
  userId: string,
  options: { limit?: number; cursor?: string } = {}
): Promise<{
  digests: Array<{ key: string; digestId: string; createdAt: string }>;
  cursor?: string;
  truncated: boolean;
}> {
  const prefix = `users/${userId}/digests/`;
  const { limit = 20, cursor } = options;

  const list = await env.DIGESTS.list({
    prefix,
    limit,
    cursor,
  });

  const digests = list.objects.map((obj) => ({
    key: obj.key,
    digestId: obj.customMetadata?.digestId || obj.key.split('/').pop()?.replace('.json', '') || '',
    createdAt: obj.uploaded.toISOString(),
  }));

  return {
    digests,
    cursor: list.truncated ? list.cursor : undefined,
    truncated: list.truncated,
  };
}

/**
 * Delete a digest from R2.
 */
export async function deleteDigest(env: Env, userId: string, digestId: string): Promise<void> {
  const key = getDigestKey(userId, digestId);
  await env.DIGESTS.delete(key);
}

/**
 * Store a cache entry in R2.
 */
export async function setCache<T>(
  env: Env,
  type: string,
  identifier: string,
  data: T,
  ttlSeconds: number = 3600
): Promise<void> {
  const key = getCacheKey(type, identifier);
  const now = new Date();
  const expiresAt = new Date(now.getTime() + ttlSeconds * 1000);

  const entry: CacheEntry<T> = {
    data,
    createdAt: now.toISOString(),
    expiresAt: expiresAt.toISOString(),
  };

  await env.CACHE.put(key, JSON.stringify(entry), {
    customMetadata: {
      type,
      expiresAt: expiresAt.toISOString(),
    },
  });
}

/**
 * Get a cache entry from R2.
 */
export async function getCache<T>(
  env: Env,
  type: string,
  identifier: string
): Promise<T | null> {
  const key = getCacheKey(type, identifier);
  const object = await env.CACHE.get(key);

  if (!object) {
    return null;
  }

  const text = await object.text();
  const entry = JSON.parse(text) as CacheEntry<T>;

  // Check if expired
  if (new Date(entry.expiresAt) < new Date()) {
    // Delete expired entry
    await env.CACHE.delete(key);
    return null;
  }

  return entry.data;
}

/**
 * Delete a cache entry.
 */
export async function deleteCache(env: Env, type: string, identifier: string): Promise<void> {
  const key = getCacheKey(type, identifier);
  await env.CACHE.delete(key);
}

/**
 * Store article content for deduplication.
 */
export async function storeArticleContent(
  env: Env,
  url: string,
  content: {
    title: string;
    text: string;
    author?: string;
    publishedDate?: string;
    wordCount: number;
  },
  ttlSeconds: number = 86400 // 24 hours
): Promise<void> {
  const urlHash = await hashUrl(url);
  await setCache(env, 'articles', urlHash, { url, ...content }, ttlSeconds);
}

/**
 * Get cached article content.
 */
export async function getArticleContent(
  env: Env,
  url: string
): Promise<{
  url: string;
  title: string;
  text: string;
  author?: string;
  publishedDate?: string;
  wordCount: number;
} | null> {
  const urlHash = await hashUrl(url);
  return getCache(env, 'articles', urlHash);
}

/**
 * Hash URL for cache key.
 */
async function hashUrl(url: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(url);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Clean up expired cache entries.
 * Should be called periodically via cron trigger.
 */
export async function cleanupExpiredCache(env: Env): Promise<{ deleted: number }> {
  const now = new Date();
  let deleted = 0;
  let cursor: string | undefined;

  do {
    const list = await env.CACHE.list({
      limit: 100,
      cursor,
    });

    for (const obj of list.objects) {
      const expiresAt = obj.customMetadata?.expiresAt;
      if (expiresAt && new Date(expiresAt) < now) {
        await env.CACHE.delete(obj.key);
        deleted++;
      }
    }

    cursor = list.truncated ? list.cursor : undefined;
  } while (cursor);

  return { deleted };
}
