/**
 * Test setup and utilities for worker tests.
 */

import { vi } from 'vitest';
import type { Env } from '../src/types';

/**
 * Create a mock environment for testing.
 */
export function createMockEnv(): Partial<Env> {
  return {
    ENVIRONMENT: 'test',
    JWT_SECRET: 'test-secret-key-for-jwt-signing',
    OPENROUTER_API_KEY: 'test-openrouter-key',
    ANTHROPIC_API_KEY: 'test-anthropic-key',
    TAVILY_API_KEY: 'test-tavily-key',
    RESEND_API_KEY: 'test-resend-key',
    DB: createMockD1Database(),
    DIGESTS: createMockR2Bucket(),
    CACHE: createMockR2Bucket(),
    RATE_LIMIT: createMockKVNamespace(),
    SESSIONS: createMockKVNamespace(),
    DIGEST_JOB: createMockDurableObjectNamespace(),
    USER_STATE: createMockDurableObjectNamespace(),
  };
}

/**
 * Create a mock D1 database.
 */
export function createMockD1Database(): D1Database {
  const storage = new Map<string, unknown[]>();

  return {
    prepare: (query: string) => {
      return {
        bind: (...args: unknown[]) => ({
          first: vi.fn().mockResolvedValue(null),
          all: vi.fn().mockResolvedValue({ results: [] }),
          run: vi.fn().mockResolvedValue({ success: true }),
        }),
        first: vi.fn().mockResolvedValue(null),
        all: vi.fn().mockResolvedValue({ results: [] }),
        run: vi.fn().mockResolvedValue({ success: true }),
      };
    },
    batch: vi.fn().mockResolvedValue([]),
    dump: vi.fn().mockResolvedValue(new ArrayBuffer(0)),
    exec: vi.fn().mockResolvedValue({ count: 0, duration: 0 }),
  } as unknown as D1Database;
}

/**
 * Create a mock R2 bucket.
 */
export function createMockR2Bucket(): R2Bucket {
  const storage = new Map<string, { body: string; metadata: Record<string, string> }>();

  return {
    put: vi.fn().mockImplementation(async (key: string, value: string | ArrayBuffer, options?: { customMetadata?: Record<string, string> }) => {
      storage.set(key, {
        body: typeof value === 'string' ? value : new TextDecoder().decode(value),
        metadata: options?.customMetadata || {},
      });
      return null;
    }),
    get: vi.fn().mockImplementation(async (key: string) => {
      const item = storage.get(key);
      if (!item) return null;
      return {
        body: new ReadableStream(),
        text: vi.fn().mockResolvedValue(item.body),
        json: vi.fn().mockResolvedValue(JSON.parse(item.body)),
        arrayBuffer: vi.fn().mockResolvedValue(new TextEncoder().encode(item.body).buffer),
        customMetadata: item.metadata,
        key,
        size: item.body.length,
        etag: 'mock-etag',
        uploaded: new Date(),
        httpEtag: '"mock-etag"',
        checksums: { toJSON: () => ({}) },
        writeHttpMetadata: vi.fn(),
      };
    }),
    delete: vi.fn().mockImplementation(async (key: string | string[]) => {
      const keys = Array.isArray(key) ? key : [key];
      keys.forEach((k) => storage.delete(k));
    }),
    list: vi.fn().mockResolvedValue({
      objects: [],
      truncated: false,
      cursor: undefined,
    }),
    head: vi.fn().mockResolvedValue(null),
    createMultipartUpload: vi.fn(),
    resumeMultipartUpload: vi.fn(),
  } as unknown as R2Bucket;
}

/**
 * Create a mock KV namespace.
 */
export function createMockKVNamespace(): KVNamespace {
  const storage = new Map<string, { value: string; metadata?: unknown }>();

  return {
    get: vi.fn().mockImplementation(async (key: string, options?: { type?: string }) => {
      const item = storage.get(key);
      if (!item) return null;
      if (options?.type === 'json') return JSON.parse(item.value);
      return item.value;
    }),
    getWithMetadata: vi.fn().mockImplementation(async (key: string) => {
      const item = storage.get(key);
      if (!item) return { value: null, metadata: null };
      return { value: item.value, metadata: item.metadata };
    }),
    put: vi.fn().mockImplementation(async (key: string, value: string, options?: { metadata?: unknown; expirationTtl?: number }) => {
      storage.set(key, { value, metadata: options?.metadata });
    }),
    delete: vi.fn().mockImplementation(async (key: string) => {
      storage.delete(key);
    }),
    list: vi.fn().mockResolvedValue({
      keys: [],
      list_complete: true,
      cursor: undefined,
    }),
  } as unknown as KVNamespace;
}

/**
 * Create a mock Durable Object namespace.
 */
export function createMockDurableObjectNamespace(): DurableObjectNamespace {
  return {
    idFromName: vi.fn().mockReturnValue({
      toString: () => 'mock-do-id',
      equals: vi.fn().mockReturnValue(true),
      name: 'mock-name',
    }),
    idFromString: vi.fn().mockReturnValue({
      toString: () => 'mock-do-id',
      equals: vi.fn().mockReturnValue(true),
    }),
    newUniqueId: vi.fn().mockReturnValue({
      toString: () => 'mock-unique-id',
      equals: vi.fn().mockReturnValue(true),
    }),
    get: vi.fn().mockReturnValue({
      fetch: vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ success: true, data: null }), {
          headers: { 'Content-Type': 'application/json' },
        })
      ),
    }),
    jurisdiction: vi.fn(),
  } as unknown as DurableObjectNamespace;
}

/**
 * Create a mock request.
 */
export function createMockRequest(
  url: string,
  options: {
    method?: string;
    headers?: Record<string, string>;
    body?: unknown;
  } = {}
): Request {
  const { method = 'GET', headers = {}, body } = options;

  return new Request(url, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * Create an authenticated mock request.
 */
export function createAuthenticatedRequest(
  url: string,
  token: string,
  options: {
    method?: string;
    body?: unknown;
  } = {}
): Request {
  return createMockRequest(url, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

/**
 * Generate a mock JWT token for testing.
 */
export function generateMockToken(
  payload: {
    userId?: string;
    email?: string;
    tier?: 'free' | 'basic' | 'pro';
  } = {}
): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = btoa(
    JSON.stringify({
      userId: payload.userId || 'test-user-id',
      email: payload.email || 'test@example.com',
      tier: payload.tier || 'free',
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 3600, // 1 hour
    })
  );
  const signature = btoa('mock-signature');
  return `${header}.${body}.${signature}`;
}

/**
 * Sample test data.
 */
export const testData = {
  user: {
    id: 'test-user-001',
    email: 'test@example.com',
    subscriptionTier: 'free' as const,
    createdAt: new Date().toISOString(),
  },
  digest: {
    id: 'digest-2025-12-25',
    userId: 'test-user-001',
    generatedAt: new Date().toISOString(),
    sections: [
      {
        topic: 'AI & Machine Learning',
        sectionSummary: 'Latest AI developments.',
        articles: [],
        crossStoryInsights: [],
      },
    ],
    metadata: {
      digestId: 'digest-2025-12-25',
      generatedAt: new Date().toISOString(),
      topicsCovered: ['AI'],
      totalArticlesFound: 100,
      totalArticlesParsed: 50,
      totalArticlesIncluded: 10,
      totalTokensUsed: 5000,
      totalCostUsd: 0.035,
      processingTimeSeconds: 45,
    },
  },
  article: {
    id: 'article-001',
    url: 'https://example.com/article',
    title: 'Test Article',
    source: 'example.com',
    summary: 'Article summary.',
    relevanceScore: 0.85,
    qualityScore: 0.78,
  },
};
