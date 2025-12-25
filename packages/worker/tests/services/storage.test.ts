/**
 * Tests for R2 storage service.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  getDigestKey,
  getCacheKey,
  storeDigest,
  getDigest,
  listUserDigests,
  deleteDigest,
  setCache,
  getCache,
  deleteCache,
} from '../../src/services/storage';
import { createMockEnv, testData } from '../setup';
import type { Env, Digest } from '../../src/types';

describe('Storage Service', () => {
  let env: Env;

  beforeEach(() => {
    env = createMockEnv() as Env;
  });

  describe('getDigestKey', () => {
    it('should generate correct key format', () => {
      const key = getDigestKey('user-123', 'digest-2025-12-25');
      expect(key).toContain('users/user-123');
      expect(key).toContain('digests');
      expect(key).toContain('digest-2025-12-25');
      expect(key).toEndWith('.json');
    });

    it('should handle different user IDs', () => {
      const key1 = getDigestKey('user-a', 'digest-1');
      const key2 = getDigestKey('user-b', 'digest-1');
      expect(key1).not.toBe(key2);
    });
  });

  describe('getCacheKey', () => {
    it('should generate correct key format', () => {
      const key = getCacheKey('articles', 'abc123');
      expect(key).toBe('cache/articles/abc123.json');
    });

    it('should handle different types', () => {
      const key1 = getCacheKey('articles', 'id');
      const key2 = getCacheKey('search', 'id');
      expect(key1).not.toBe(key2);
    });
  });

  describe('storeDigest', () => {
    it('should store digest in R2', async () => {
      const digest = testData.digest as unknown as Digest;
      const markdown = '# Test Digest\n\nContent here.';

      const key = await storeDigest(
        env,
        'user-123',
        'digest-2025-12-25',
        digest,
        markdown
      );

      expect(env.DIGESTS.put).toHaveBeenCalled();
      expect(key).toContain('user-123');
    });

    it('should include custom metadata', async () => {
      const digest = testData.digest as unknown as Digest;

      await storeDigest(env, 'user-123', 'digest-001', digest, 'markdown');

      expect(env.DIGESTS.put).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(String),
        expect.objectContaining({
          customMetadata: expect.any(Object),
        })
      );
    });
  });

  describe('getDigest', () => {
    it('should return null for nonexistent digest', async () => {
      vi.mocked(env.DIGESTS.get).mockResolvedValue(null);

      const result = await getDigest(env, 'user-123', 'nonexistent');
      expect(result).toBeNull();
    });

    it('should return digest when found', async () => {
      const storedData = {
        digest: testData.digest,
        markdown: '# Digest',
        createdAt: new Date().toISOString(),
      };

      vi.mocked(env.DIGESTS.get).mockResolvedValue({
        text: vi.fn().mockResolvedValue(JSON.stringify(storedData)),
      } as unknown as R2ObjectBody);

      const result = await getDigest(env, 'user-123', 'digest-001');
      expect(result).not.toBeNull();
      expect(result?.digest).toBeDefined();
    });
  });

  describe('listUserDigests', () => {
    it('should return empty list for new user', async () => {
      const result = await listUserDigests(env, 'new-user');
      expect(result.digests).toEqual([]);
      expect(result.truncated).toBe(false);
    });

    it('should handle pagination', async () => {
      vi.mocked(env.DIGESTS.list).mockResolvedValue({
        objects: [
          { key: 'digest-1.json', customMetadata: { digestId: 'digest-1' }, uploaded: new Date() },
          { key: 'digest-2.json', customMetadata: { digestId: 'digest-2' }, uploaded: new Date() },
        ],
        truncated: true,
        cursor: 'next-cursor',
      } as unknown as R2Objects);

      const result = await listUserDigests(env, 'user-123', { limit: 2 });
      expect(result.truncated).toBe(true);
      expect(result.cursor).toBe('next-cursor');
    });
  });

  describe('deleteDigest', () => {
    it('should delete digest from R2', async () => {
      await deleteDigest(env, 'user-123', 'digest-001');
      expect(env.DIGESTS.delete).toHaveBeenCalled();
    });
  });

  describe('Cache operations', () => {
    describe('setCache', () => {
      it('should store cache entry', async () => {
        await setCache(env, 'articles', 'hash123', { title: 'Test' });
        expect(env.CACHE.put).toHaveBeenCalled();
      });

      it('should include TTL in metadata', async () => {
        await setCache(env, 'articles', 'hash123', { data: 'test' }, 3600);
        expect(env.CACHE.put).toHaveBeenCalledWith(
          expect.any(String),
          expect.any(String),
          expect.objectContaining({
            customMetadata: expect.objectContaining({
              expiresAt: expect.any(String),
            }),
          })
        );
      });
    });

    describe('getCache', () => {
      it('should return null for nonexistent cache', async () => {
        vi.mocked(env.CACHE.get).mockResolvedValue(null);

        const result = await getCache(env, 'articles', 'nonexistent');
        expect(result).toBeNull();
      });

      it('should return null for expired cache', async () => {
        const expiredEntry = {
          data: { test: true },
          createdAt: new Date(Date.now() - 7200000).toISOString(),
          expiresAt: new Date(Date.now() - 3600000).toISOString(), // Expired 1 hour ago
        };

        vi.mocked(env.CACHE.get).mockResolvedValue({
          text: vi.fn().mockResolvedValue(JSON.stringify(expiredEntry)),
        } as unknown as R2ObjectBody);

        const result = await getCache(env, 'articles', 'expired');
        expect(result).toBeNull();
      });
    });

    describe('deleteCache', () => {
      it('should delete cache entry', async () => {
        await deleteCache(env, 'articles', 'hash123');
        expect(env.CACHE.delete).toHaveBeenCalled();
      });
    });
  });
});

describe('Storage Key Generation', () => {
  it('should create deterministic keys', () => {
    const key1 = getDigestKey('user', 'digest');
    const key2 = getDigestKey('user', 'digest');
    expect(key1).toBe(key2);
  });

  it('should create unique keys for different inputs', () => {
    const key1 = getDigestKey('user1', 'digest1');
    const key2 = getDigestKey('user2', 'digest2');
    expect(key1).not.toBe(key2);
  });

  it('should handle special characters in IDs', () => {
    const key = getDigestKey('user-with-dashes', 'digest_with_underscores');
    expect(key).toContain('user-with-dashes');
    expect(key).toContain('digest_with_underscores');
  });
});
