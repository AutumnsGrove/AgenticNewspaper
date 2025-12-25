/**
 * Tests for type definitions.
 */

import { describe, it, expect } from 'vitest';
import type {
  User,
  UserPreferences,
  Topic,
  DeliveryConfig,
  StyleConfig,
  ThresholdConfig,
  Article,
  BiasDirection,
  Digest,
  DigestMetadata,
  DigestSection,
  DigestJobState,
  JobStatus,
  ApiResponse,
  ApiError,
  UsageLimits,
  USAGE_LIMITS,
} from '../../src/types';

describe('Type Definitions', () => {
  describe('User types', () => {
    it('should define User structure', () => {
      const user: User = {
        id: 'user-123',
        email: 'test@example.com',
        createdAt: new Date().toISOString(),
        subscriptionTier: 'free',
        preferences: {
          topics: [],
          sources: [],
          delivery: {
            frequency: 'daily_am',
            deliveryTimeUtc: '06:00',
            channels: ['web'],
            lookbackHours: 24,
            timezone: 'UTC',
          },
          style: {
            tone: 'hn-style',
            skepticismLevel: 3,
            technicalDepth: 3,
            includeBiasAnalysis: true,
            includeCrossConnections: true,
            maxArticlesPerTopic: 5,
          },
          thresholds: {
            minRelevanceScore: 0.6,
            minQualityScore: 0.5,
            minNoveltyScore: 0.3,
            maxBiasScore: 0.8,
          },
        },
      };

      expect(user.id).toBe('user-123');
      expect(user.subscriptionTier).toBe('free');
    });

    it('should allow optional rssToken', () => {
      const userWithToken: User = {
        id: 'user-123',
        email: 'test@example.com',
        createdAt: new Date().toISOString(),
        subscriptionTier: 'pro',
        preferences: {} as UserPreferences,
        rssToken: 'token-abc',
      };

      expect(userWithToken.rssToken).toBe('token-abc');
    });
  });

  describe('Topic types', () => {
    it('should define Topic structure', () => {
      const topic: Topic = {
        name: 'AI & Machine Learning',
        keywords: ['AI', 'ML', 'LLM'],
        priority: 5,
        enabled: true,
      };

      expect(topic.name).toBe('AI & Machine Learning');
      expect(topic.keywords.length).toBe(3);
      expect(topic.priority).toBe(5);
    });
  });

  describe('Delivery types', () => {
    it('should define valid frequencies', () => {
      const frequencies: DeliveryConfig['frequency'][] = [
        'hourly',
        'daily_am',
        'daily_pm',
        'weekly',
        'biweekly',
        'monthly',
      ];

      frequencies.forEach((freq) => {
        const config: DeliveryConfig = {
          frequency: freq,
          deliveryTimeUtc: '06:00',
          channels: ['web'],
          lookbackHours: 24,
          timezone: 'UTC',
        };
        expect(config.frequency).toBe(freq);
      });
    });

    it('should define valid channels', () => {
      const config: DeliveryConfig = {
        frequency: 'daily_am',
        deliveryTimeUtc: '06:00',
        channels: ['web', 'rss', 'email'],
        lookbackHours: 24,
        timezone: 'UTC',
      };

      expect(config.channels).toContain('web');
      expect(config.channels).toContain('rss');
      expect(config.channels).toContain('email');
    });
  });

  describe('Style types', () => {
    it('should define valid tones', () => {
      const tones: StyleConfig['tone'][] = ['hn-style', 'formal', 'casual'];

      tones.forEach((tone) => {
        const config: StyleConfig = {
          tone,
          skepticismLevel: 3,
          technicalDepth: 3,
          includeBiasAnalysis: true,
          includeCrossConnections: true,
          maxArticlesPerTopic: 5,
        };
        expect(config.tone).toBe(tone);
      });
    });
  });

  describe('Article types', () => {
    it('should define Article structure', () => {
      const article: Article = {
        id: 'article-123',
        url: 'https://example.com/article',
        title: 'Test Article',
        source: 'example.com',
        wordCount: 1000,
        readingTimeMinutes: 5,
        summary: 'Article summary',
        keyPoints: ['Point 1', 'Point 2'],
        technicalInsights: [],
        relevanceScore: 0.85,
        qualityScore: 0.78,
        noveltyScore: 0.72,
        biasScore: 0.5,
        biasDirection: 'center',
        redFlags: [],
        technicalLevel: 3,
      };

      expect(article.id).toBe('article-123');
      expect(article.relevanceScore).toBe(0.85);
    });

    it('should define valid BiasDirection values', () => {
      const directions: BiasDirection[] = [
        'left',
        'center-left',
        'center',
        'center-right',
        'right',
        'unknown',
      ];

      directions.forEach((dir) => {
        expect(dir.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Digest types', () => {
    it('should define Digest structure', () => {
      const digest: Digest = {
        metadata: {
          digestId: 'digest-123',
          generatedAt: new Date().toISOString(),
          topicsCovered: ['AI'],
          totalArticlesFound: 100,
          totalArticlesParsed: 50,
          totalArticlesIncluded: 10,
          totalTokensUsed: 5000,
          totalCostUsd: 0.035,
          processingTimeSeconds: 45,
        },
        sections: [],
      };

      expect(digest.metadata.digestId).toBe('digest-123');
      expect(digest.sections).toEqual([]);
    });

    it('should define DigestSection structure', () => {
      const section: DigestSection = {
        topic: 'AI',
        sectionSummary: 'Summary of AI news',
        articles: [],
        crossStoryInsights: ['Insight 1'],
      };

      expect(section.topic).toBe('AI');
      expect(section.crossStoryInsights.length).toBe(1);
    });
  });

  describe('Job types', () => {
    it('should define valid JobStatus values', () => {
      const statuses: JobStatus[] = [
        'pending',
        'searching',
        'fetching',
        'parsing',
        'analyzing',
        'synthesizing',
        'complete',
        'failed',
      ];

      expect(statuses.length).toBe(8);
    });

    it('should define DigestJobState structure', () => {
      const state: DigestJobState = {
        id: 'job-123',
        userId: 'user-123',
        status: 'analyzing',
        batchNum: 1,
        articlesFound: 50,
        articlesParsed: 40,
        articlesAnalyzed: 30,
        startedAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      expect(state.status).toBe('analyzing');
      expect(state.articlesAnalyzed).toBe(30);
    });
  });

  describe('API types', () => {
    it('should define ApiResponse structure', () => {
      const response: ApiResponse<{ data: string }> = {
        success: true,
        data: { data: 'test' },
      };

      expect(response.success).toBe(true);
      expect(response.data).toBeDefined();
    });

    it('should define ApiError structure', () => {
      const error: ApiError = {
        code: 'VALIDATION_ERROR',
        message: 'Invalid input',
        details: { field: 'email' },
      };

      expect(error.code).toBe('VALIDATION_ERROR');
      expect(error.details?.field).toBe('email');
    });
  });

  describe('Usage limits', () => {
    it('should define USAGE_LIMITS constant', () => {
      expect(USAGE_LIMITS.free).toBeDefined();
      expect(USAGE_LIMITS.basic).toBeDefined();
      expect(USAGE_LIMITS.pro).toBeDefined();
    });

    it('should have correct free tier limits', () => {
      const free = USAGE_LIMITS.free;
      expect(free.maxDigestsPerMonth).toBe(4);
      expect(free.maxArticlesPerDigest).toBe(10);
      expect(free.maxTopics).toBe(3);
    });

    it('should have correct pro tier limits', () => {
      const pro = USAGE_LIMITS.pro;
      expect(pro.maxDigestsPerMonth).toBe(-1); // unlimited
      expect(pro.maxTopics).toBe(-1); // unlimited
    });

    it('should have increasing limits per tier', () => {
      expect(USAGE_LIMITS.basic.maxDigestsPerMonth).toBeGreaterThan(
        USAGE_LIMITS.free.maxDigestsPerMonth
      );
      expect(USAGE_LIMITS.basic.maxArticlesPerDigest).toBeGreaterThan(
        USAGE_LIMITS.free.maxArticlesPerDigest
      );
    });
  });
});

describe('Type Safety', () => {
  it('should enforce required fields', () => {
    // This is a compile-time check - if it compiles, the types are correct
    const metadata: DigestMetadata = {
      digestId: 'test',
      generatedAt: new Date().toISOString(),
      topicsCovered: [],
      totalArticlesFound: 0,
      totalArticlesParsed: 0,
      totalArticlesIncluded: 0,
      totalTokensUsed: 0,
      totalCostUsd: 0,
      processingTimeSeconds: 0,
    };

    expect(Object.keys(metadata).length).toBe(9);
  });

  it('should allow optional fields', () => {
    const digest: Digest = {
      metadata: {
        digestId: 'test',
        generatedAt: new Date().toISOString(),
        topicsCovered: [],
        totalArticlesFound: 0,
        totalArticlesParsed: 0,
        totalArticlesIncluded: 0,
        totalTokensUsed: 0,
        totalCostUsd: 0,
        processingTimeSeconds: 0,
      },
      sections: [],
      crossStoryConnections: 'Optional connection',
      skepticsSummary: 'Optional skeptic note',
    };

    expect(digest.crossStoryConnections).toBeDefined();
    expect(digest.skepticsSummary).toBeDefined();
  });
});
