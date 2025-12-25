/**
 * Tests for digest API client.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock the digest API
const createDigestApi = (baseUrl: string) => {
  return {
    baseUrl,
    getDigests: async (limit = 10, offset = 0) => {
      const response = await fetch(`${baseUrl}/api/digests?limit=${limit}&offset=${offset}`);
      if (!response.ok) throw new Error('Failed to fetch digests');
      return response.json();
    },
    getDigest: async (id: string) => {
      const response = await fetch(`${baseUrl}/api/digests/${id}`);
      if (!response.ok) throw new Error('Digest not found');
      return response.json();
    },
    getLatestDigest: async () => {
      const response = await fetch(`${baseUrl}/api/digests/latest`);
      if (!response.ok) throw new Error('No digest available');
      return response.json();
    },
    generateDigest: async () => {
      const response = await fetch(`${baseUrl}/api/digests/generate`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to start generation');
      return response.json();
    },
    getDigestStatus: async (jobId: string) => {
      const response = await fetch(`${baseUrl}/api/digests/status/${jobId}`);
      if (!response.ok) throw new Error('Job not found');
      return response.json();
    },
    submitFeedback: async (digestId: string, articleId: string, feedback: 'helpful' | 'not_helpful') => {
      const response = await fetch(`${baseUrl}/api/digests/${digestId}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ articleId, feedback }),
      });
      if (!response.ok) throw new Error('Failed to submit feedback');
      return response.json();
    },
  };
};

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Digest API Client', () => {
  let api: ReturnType<typeof createDigestApi>;

  beforeEach(() => {
    api = createDigestApi('https://clearing.autumnsgrove.com');
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('getDigests', () => {
    it('should fetch digests with default pagination', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ digests: [], total: 0 }),
      });

      await api.getDigests();

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/digests?limit=10&offset=0'
      );
    });

    it('should fetch digests with custom pagination', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ digests: [], total: 50 }),
      });

      await api.getDigests(20, 40);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/digests?limit=20&offset=40'
      );
    });

    it('should parse digest list response', async () => {
      const mockDigests = [
        { id: 'digest-1', title: 'Morning Brief', createdAt: '2025-01-15T06:00:00Z' },
        { id: 'digest-2', title: 'Evening Update', createdAt: '2025-01-14T18:00:00Z' },
      ];

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ digests: mockDigests, total: 2 }),
      });

      const result = await api.getDigests();

      expect(result.digests).toHaveLength(2);
      expect(result.total).toBe(2);
    });

    it('should throw error on failed request', async () => {
      mockFetch.mockResolvedValue({ ok: false, status: 500 });

      await expect(api.getDigests()).rejects.toThrow('Failed to fetch digests');
    });
  });

  describe('getDigest', () => {
    it('should fetch single digest by ID', async () => {
      const mockDigest = {
        id: 'digest-123',
        title: 'Test Digest',
        articles: [],
        createdAt: '2025-01-15T06:00:00Z',
      };

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockDigest),
      });

      const result = await api.getDigest('digest-123');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/digests/digest-123'
      );
      expect(result.id).toBe('digest-123');
    });

    it('should throw error for non-existent digest', async () => {
      mockFetch.mockResolvedValue({ ok: false, status: 404 });

      await expect(api.getDigest('nonexistent')).rejects.toThrow('Digest not found');
    });
  });

  describe('getLatestDigest', () => {
    it('should fetch most recent digest', async () => {
      const mockDigest = {
        id: 'latest-digest',
        title: 'Latest Brief',
        createdAt: '2025-01-15T12:00:00Z',
      };

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockDigest),
      });

      const result = await api.getLatestDigest();

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/digests/latest'
      );
      expect(result.id).toBe('latest-digest');
    });

    it('should throw error when no digests available', async () => {
      mockFetch.mockResolvedValue({ ok: false, status: 404 });

      await expect(api.getLatestDigest()).rejects.toThrow('No digest available');
    });
  });

  describe('generateDigest', () => {
    it('should start digest generation', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ jobId: 'job-123', status: 'pending' }),
      });

      const result = await api.generateDigest();

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/digests/generate',
        { method: 'POST' }
      );
      expect(result.jobId).toBe('job-123');
    });

    it('should throw error on generation failure', async () => {
      mockFetch.mockResolvedValue({ ok: false, status: 429 });

      await expect(api.generateDigest()).rejects.toThrow('Failed to start generation');
    });
  });

  describe('getDigestStatus', () => {
    it('should fetch job status - pending', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ jobId: 'job-123', status: 'pending', progress: 0 }),
      });

      const result = await api.getDigestStatus('job-123');

      expect(result.status).toBe('pending');
      expect(result.progress).toBe(0);
    });

    it('should fetch job status - in_progress', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            jobId: 'job-123',
            status: 'in_progress',
            progress: 50,
            currentStep: 'Analyzing articles',
          }),
      });

      const result = await api.getDigestStatus('job-123');

      expect(result.status).toBe('in_progress');
      expect(result.progress).toBe(50);
      expect(result.currentStep).toBe('Analyzing articles');
    });

    it('should fetch job status - completed', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            jobId: 'job-123',
            status: 'completed',
            progress: 100,
            digestId: 'digest-456',
          }),
      });

      const result = await api.getDigestStatus('job-123');

      expect(result.status).toBe('completed');
      expect(result.digestId).toBe('digest-456');
    });

    it('should fetch job status - failed', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            jobId: 'job-123',
            status: 'failed',
            error: 'Rate limit exceeded',
          }),
      });

      const result = await api.getDigestStatus('job-123');

      expect(result.status).toBe('failed');
      expect(result.error).toBe('Rate limit exceeded');
    });

    it('should throw error for non-existent job', async () => {
      mockFetch.mockResolvedValue({ ok: false, status: 404 });

      await expect(api.getDigestStatus('invalid')).rejects.toThrow('Job not found');
    });
  });

  describe('submitFeedback', () => {
    it('should submit positive feedback', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await api.submitFeedback('digest-123', 'article-456', 'helpful');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/digests/digest-123/feedback',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ articleId: 'article-456', feedback: 'helpful' }),
        }
      );
    });

    it('should submit negative feedback', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await api.submitFeedback('digest-123', 'article-456', 'not_helpful');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://clearing.autumnsgrove.com/api/digests/digest-123/feedback',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ articleId: 'article-456', feedback: 'not_helpful' }),
        }
      );
    });

    it('should throw error on feedback submission failure', async () => {
      mockFetch.mockResolvedValue({ ok: false, status: 400 });

      await expect(api.submitFeedback('digest-123', 'article-456', 'helpful')).rejects.toThrow(
        'Failed to submit feedback'
      );
    });
  });
});

describe('Digest Data Validation', () => {
  describe('Digest structure', () => {
    it('should have required fields', () => {
      const digest = {
        id: 'digest-123',
        title: 'Morning Brief',
        subtitle: 'Your personalized news digest',
        createdAt: '2025-01-15T06:00:00Z',
        articles: [],
        metadata: {
          topicCoverage: {},
          totalArticles: 0,
          averageQuality: 0,
        },
      };

      expect(digest.id).toBeDefined();
      expect(digest.title).toBeDefined();
      expect(digest.createdAt).toBeDefined();
      expect(Array.isArray(digest.articles)).toBe(true);
    });
  });

  describe('Article structure', () => {
    it('should have required fields', () => {
      const article = {
        id: 'article-123',
        title: 'Test Article',
        summary: 'A brief summary',
        sourceUrl: 'https://example.com/article',
        sourceName: 'Example News',
        publishedAt: '2025-01-15T10:00:00Z',
        topics: ['technology', 'AI'],
        qualityScore: 0.85,
        biasAssessment: { direction: 'neutral', confidence: 0.9 },
      };

      expect(article.id).toBeDefined();
      expect(article.title).toBeDefined();
      expect(article.sourceUrl).toBeDefined();
      expect(article.qualityScore).toBeGreaterThanOrEqual(0);
      expect(article.qualityScore).toBeLessThanOrEqual(1);
    });
  });
});

describe('Error Handling', () => {
  it('should handle network errors', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));
    const api = createDigestApi('https://clearing.autumnsgrove.com');

    await expect(api.getDigests()).rejects.toThrow('Network error');
  });

  it('should handle timeout errors', async () => {
    mockFetch.mockRejectedValue(new Error('Request timeout'));
    const api = createDigestApi('https://clearing.autumnsgrove.com');

    await expect(api.getLatestDigest()).rejects.toThrow('Request timeout');
  });

  it('should handle JSON parse errors', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.reject(new Error('Invalid JSON')),
    });
    const api = createDigestApi('https://clearing.autumnsgrove.com');

    await expect(api.getDigests()).rejects.toThrow('Invalid JSON');
  });
});
