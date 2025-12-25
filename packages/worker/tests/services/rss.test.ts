/**
 * Tests for RSS feed generation.
 */

import { describe, it, expect } from 'vitest';
import { generateRssFeed, parseRssFeed } from '../../src/services/rss';
import type { Digest } from '../../src/types';

describe('RSS Feed Generation', () => {
  const sampleDigest: Digest = {
    metadata: {
      digestId: 'digest-2025-12-25',
      generatedAt: '2025-12-25T06:00:00Z',
      topicsCovered: ['AI & Machine Learning', 'Science'],
      totalArticlesFound: 100,
      totalArticlesParsed: 50,
      totalArticlesIncluded: 10,
      totalTokensUsed: 5000,
      totalCostUsd: 0.035,
      processingTimeSeconds: 45,
    },
    sections: [
      {
        topic: 'AI & Machine Learning',
        sectionSummary: 'Major developments in AI this week.',
        articles: [
          {
            id: 'article-1',
            url: 'https://example.com/ai-article',
            title: 'AI Breakthrough Announced',
            source: 'example.com',
            summary: 'Researchers announce major AI breakthrough.',
            keyPoints: ['Point 1', 'Point 2'],
            relevanceScore: 0.9,
            qualityScore: 0.85,
            noveltyScore: 0.8,
            biasScore: 0.5,
            biasDirection: 'center',
            technicalLevel: 3,
            readingTimeMinutes: 5,
            wordCount: 1000,
            technicalInsights: [],
            redFlags: [],
          },
        ],
        crossStoryInsights: ['Pattern observed across articles'],
      },
    ],
    crossStoryConnections: 'Connection between stories.',
    skepticsSummary: 'Some claims need verification.',
  };

  const feedOptions = {
    userId: 'user-123',
    userEmail: 'test@example.com',
    rssToken: 'token-abc',
    baseUrl: 'https://clearing.autumnsgrove.com',
  };

  describe('generateRssFeed', () => {
    it('should generate valid RSS XML', () => {
      const digests = [{ digest: sampleDigest, digestId: 'digest-2025-12-25' }];
      const xml = generateRssFeed(digests, feedOptions);

      expect(xml).toContain('<?xml version="1.0"');
      expect(xml).toContain('<rss version="2.0"');
      expect(xml).toContain('</rss>');
    });

    it('should include channel information', () => {
      const digests = [{ digest: sampleDigest, digestId: 'digest-2025-12-25' }];
      const xml = generateRssFeed(digests, feedOptions);

      expect(xml).toContain('<channel>');
      expect(xml).toContain('<title>');
      expect(xml).toContain('<link>');
      expect(xml).toContain('<description>');
    });

    it('should include user email in title', () => {
      const digests = [{ digest: sampleDigest, digestId: 'digest-2025-12-25' }];
      const xml = generateRssFeed(digests, feedOptions);

      expect(xml).toContain('test@example.com');
    });

    it('should include atom self link', () => {
      const digests = [{ digest: sampleDigest, digestId: 'digest-2025-12-25' }];
      const xml = generateRssFeed(digests, feedOptions);

      expect(xml).toContain('xmlns:atom');
      expect(xml).toContain('rel="self"');
    });

    it('should generate items for each digest', () => {
      const digests = [
        { digest: sampleDigest, digestId: 'digest-1' },
        { digest: sampleDigest, digestId: 'digest-2' },
      ];
      const xml = generateRssFeed(digests, feedOptions);

      const itemCount = (xml.match(/<item>/g) || []).length;
      expect(itemCount).toBe(2);
    });

    it('should include guid for each item', () => {
      const digests = [{ digest: sampleDigest, digestId: 'digest-2025-12-25' }];
      const xml = generateRssFeed(digests, feedOptions);

      expect(xml).toContain('<guid');
      expect(xml).toContain('</guid>');
    });

    it('should include pubDate for each item', () => {
      const digests = [{ digest: sampleDigest, digestId: 'digest-2025-12-25' }];
      const xml = generateRssFeed(digests, feedOptions);

      expect(xml).toContain('<pubDate>');
    });

    it('should include categories from topics', () => {
      const digests = [{ digest: sampleDigest, digestId: 'digest-2025-12-25' }];
      const xml = generateRssFeed(digests, feedOptions);

      expect(xml).toContain('<category>');
      expect(xml).toContain('AI');
    });

    it('should include content:encoded', () => {
      const digests = [{ digest: sampleDigest, digestId: 'digest-2025-12-25' }];
      const xml = generateRssFeed(digests, feedOptions);

      expect(xml).toContain('xmlns:content');
      expect(xml).toContain('<content:encoded>');
    });

    it('should escape special characters', () => {
      const digestWithSpecialChars: Digest = {
        ...sampleDigest,
        sections: [
          {
            ...sampleDigest.sections[0],
            sectionSummary: 'Summary with <script> & special "chars"',
          },
        ],
      };

      const digests = [{ digest: digestWithSpecialChars, digestId: 'digest-1' }];
      const xml = generateRssFeed(digests, feedOptions);

      // Should escape < and &
      expect(xml).not.toContain('<script>');
      expect(xml).toContain('&lt;');
      expect(xml).toContain('&amp;');
    });

    it('should handle empty digest list', () => {
      const xml = generateRssFeed([], feedOptions);

      expect(xml).toContain('<channel>');
      expect(xml).not.toContain('<item>');
    });
  });

  describe('parseRssFeed', () => {
    it('should parse RSS XML and extract items', () => {
      const digests = [{ digest: sampleDigest, digestId: 'digest-2025-12-25' }];
      const xml = generateRssFeed(digests, feedOptions);

      const items = parseRssFeed(xml);
      expect(items.length).toBe(1);
    });

    it('should extract title from items', () => {
      const digests = [{ digest: sampleDigest, digestId: 'digest-2025-12-25' }];
      const xml = generateRssFeed(digests, feedOptions);

      const items = parseRssFeed(xml);
      expect(items[0].title).toContain('The Daily Clearing');
    });

    it('should extract link from items', () => {
      const digests = [{ digest: sampleDigest, digestId: 'digest-2025-12-25' }];
      const xml = generateRssFeed(digests, feedOptions);

      const items = parseRssFeed(xml);
      expect(items[0].link).toContain('clearing.autumnsgrove.com');
    });

    it('should extract pubDate from items', () => {
      const digests = [{ digest: sampleDigest, digestId: 'digest-2025-12-25' }];
      const xml = generateRssFeed(digests, feedOptions);

      const items = parseRssFeed(xml);
      expect(items[0].pubDate).toBeDefined();
    });

    it('should handle multiple items', () => {
      const digests = [
        { digest: sampleDigest, digestId: 'digest-1' },
        { digest: sampleDigest, digestId: 'digest-2' },
        { digest: sampleDigest, digestId: 'digest-3' },
      ];
      const xml = generateRssFeed(digests, feedOptions);

      const items = parseRssFeed(xml);
      expect(items.length).toBe(3);
    });
  });

  describe('Feed Content', () => {
    it('should include article links in description', () => {
      const digests = [{ digest: sampleDigest, digestId: 'digest-2025-12-25' }];
      const xml = generateRssFeed(digests, feedOptions);

      expect(xml).toContain('https://example.com/ai-article');
    });

    it('should include article titles', () => {
      const digests = [{ digest: sampleDigest, digestId: 'digest-2025-12-25' }];
      const xml = generateRssFeed(digests, feedOptions);

      expect(xml).toContain('AI Breakthrough Announced');
    });

    it('should include section summaries', () => {
      const digests = [{ digest: sampleDigest, digestId: 'digest-2025-12-25' }];
      const xml = generateRssFeed(digests, feedOptions);

      expect(xml).toContain('Major developments in AI');
    });

    it('should include cross-story connections', () => {
      const digests = [{ digest: sampleDigest, digestId: 'digest-2025-12-25' }];
      const xml = generateRssFeed(digests, feedOptions);

      expect(xml).toContain('Connection between stories');
    });
  });
});

describe('RSS Date Formatting', () => {
  it('should format dates in RFC 822 format', () => {
    const sampleDigest: Digest = {
      metadata: {
        digestId: 'test',
        generatedAt: '2025-12-25T06:00:00Z',
        topicsCovered: [],
        totalArticlesFound: 0,
        totalArticlesParsed: 0,
        totalArticlesIncluded: 0,
        totalTokensUsed: 0,
        totalCostUsd: 0,
        processingTimeSeconds: 0,
      },
      sections: [],
    };

    const digests = [{ digest: sampleDigest, digestId: 'test' }];
    const xml = generateRssFeed(digests, {
      userId: 'user',
      userEmail: 'test@test.com',
      rssToken: 'token',
      baseUrl: 'https://example.com',
    });

    // Should contain a properly formatted date
    expect(xml).toMatch(/<pubDate>.*2025.*<\/pubDate>/);
  });
});
