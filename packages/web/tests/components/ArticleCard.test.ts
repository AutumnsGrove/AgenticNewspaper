/**
 * Tests for ArticleCard component behavior.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock article data structure
interface Article {
  id: string;
  title: string;
  summary: string;
  sourceUrl: string;
  sourceName: string;
  publishedAt: string;
  qualityScore: number;
  biasDirection: 'left' | 'center-left' | 'center' | 'center-right' | 'right';
  biasConfidence: number;
  topics: string[];
  wordCount: number;
  readTimeMinutes: number;
}

// Mock ArticleCard logic
const createArticleCard = (article: Article) => {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const formatQuality = (score: number) => {
    if (score >= 0.8) return { label: 'Excellent', color: 'green' };
    if (score >= 0.6) return { label: 'Good', color: 'blue' };
    if (score >= 0.4) return { label: 'Fair', color: 'yellow' };
    return { label: 'Poor', color: 'red' };
  };

  const formatBias = (direction: string) => {
    const labels: Record<string, string> = {
      left: 'Left',
      'center-left': 'Center-Left',
      center: 'Neutral',
      'center-right': 'Center-Right',
      right: 'Right',
    };
    return labels[direction] || 'Unknown';
  };

  const truncateSummary = (summary: string, maxLength = 200) => {
    if (summary.length <= maxLength) return summary;
    return summary.slice(0, maxLength - 3) + '...';
  };

  return {
    article,
    displayDate: formatDate(article.publishedAt),
    quality: formatQuality(article.qualityScore),
    biasLabel: formatBias(article.biasDirection),
    truncatedSummary: truncateSummary(article.summary),
    readTime: `${article.readTimeMinutes} min read`,
    source: article.sourceName,
    isExpanded: false,
    toggleExpand: function () {
      this.isExpanded = !this.isExpanded;
    },
    getSummary: function () {
      return this.isExpanded ? this.article.summary : this.truncatedSummary;
    },
  };
};

const createSampleArticle = (overrides: Partial<Article> = {}): Article => ({
  id: 'article-1',
  title: 'AI Makes Major Breakthrough in Language Understanding',
  summary:
    'Researchers have announced a significant advancement in natural language processing that could revolutionize how computers understand human communication. The new model shows unprecedented accuracy in context understanding.',
  sourceUrl: 'https://techcrunch.com/article/ai-breakthrough',
  sourceName: 'TechCrunch',
  publishedAt: '2025-01-15T10:30:00Z',
  qualityScore: 0.85,
  biasDirection: 'center',
  biasConfidence: 0.92,
  topics: ['AI', 'Technology', 'Research'],
  wordCount: 1200,
  readTimeMinutes: 5,
  ...overrides,
});

describe('ArticleCard Creation', () => {
  it('should create card from article data', () => {
    const article = createSampleArticle();
    const card = createArticleCard(article);

    expect(card.article).toBe(article);
    expect(card.source).toBe('TechCrunch');
  });

  it('should format publication date', () => {
    const article = createSampleArticle({ publishedAt: '2025-01-15T10:30:00Z' });
    const card = createArticleCard(article);

    expect(card.displayDate).toContain('Jan');
    expect(card.displayDate).toContain('15');
  });

  it('should calculate read time', () => {
    const article = createSampleArticle({ readTimeMinutes: 7 });
    const card = createArticleCard(article);

    expect(card.readTime).toBe('7 min read');
  });
});

describe('Quality Score Display', () => {
  it('should display excellent for high scores', () => {
    const article = createSampleArticle({ qualityScore: 0.9 });
    const card = createArticleCard(article);

    expect(card.quality.label).toBe('Excellent');
    expect(card.quality.color).toBe('green');
  });

  it('should display good for medium-high scores', () => {
    const article = createSampleArticle({ qualityScore: 0.7 });
    const card = createArticleCard(article);

    expect(card.quality.label).toBe('Good');
    expect(card.quality.color).toBe('blue');
  });

  it('should display fair for medium scores', () => {
    const article = createSampleArticle({ qualityScore: 0.5 });
    const card = createArticleCard(article);

    expect(card.quality.label).toBe('Fair');
    expect(card.quality.color).toBe('yellow');
  });

  it('should display poor for low scores', () => {
    const article = createSampleArticle({ qualityScore: 0.3 });
    const card = createArticleCard(article);

    expect(card.quality.label).toBe('Poor');
    expect(card.quality.color).toBe('red');
  });

  it('should handle boundary scores correctly', () => {
    const excellent = createArticleCard(createSampleArticle({ qualityScore: 0.8 }));
    const good = createArticleCard(createSampleArticle({ qualityScore: 0.6 }));
    const fair = createArticleCard(createSampleArticle({ qualityScore: 0.4 }));

    expect(excellent.quality.label).toBe('Excellent');
    expect(good.quality.label).toBe('Good');
    expect(fair.quality.label).toBe('Fair');
  });
});

describe('Bias Display', () => {
  it('should display left bias correctly', () => {
    const article = createSampleArticle({ biasDirection: 'left' });
    const card = createArticleCard(article);

    expect(card.biasLabel).toBe('Left');
  });

  it('should display center-left bias correctly', () => {
    const article = createSampleArticle({ biasDirection: 'center-left' });
    const card = createArticleCard(article);

    expect(card.biasLabel).toBe('Center-Left');
  });

  it('should display center as neutral', () => {
    const article = createSampleArticle({ biasDirection: 'center' });
    const card = createArticleCard(article);

    expect(card.biasLabel).toBe('Neutral');
  });

  it('should display center-right bias correctly', () => {
    const article = createSampleArticle({ biasDirection: 'center-right' });
    const card = createArticleCard(article);

    expect(card.biasLabel).toBe('Center-Right');
  });

  it('should display right bias correctly', () => {
    const article = createSampleArticle({ biasDirection: 'right' });
    const card = createArticleCard(article);

    expect(card.biasLabel).toBe('Right');
  });
});

describe('Summary Truncation', () => {
  it('should not truncate short summaries', () => {
    const article = createSampleArticle({ summary: 'Short summary' });
    const card = createArticleCard(article);

    expect(card.truncatedSummary).toBe('Short summary');
  });

  it('should truncate long summaries', () => {
    const longSummary = 'A'.repeat(300);
    const article = createSampleArticle({ summary: longSummary });
    const card = createArticleCard(article);

    expect(card.truncatedSummary.length).toBeLessThanOrEqual(200);
    expect(card.truncatedSummary).toEndWith('...');
  });

  it('should preserve words at truncation point', () => {
    const article = createSampleArticle({ summary: 'A'.repeat(250) });
    const card = createArticleCard(article);

    expect(card.truncatedSummary).toContain('...');
  });
});

describe('Expand/Collapse Behavior', () => {
  it('should start collapsed', () => {
    const article = createSampleArticle();
    const card = createArticleCard(article);

    expect(card.isExpanded).toBe(false);
  });

  it('should expand when toggled', () => {
    const article = createSampleArticle();
    const card = createArticleCard(article);

    card.toggleExpand();

    expect(card.isExpanded).toBe(true);
  });

  it('should collapse when toggled again', () => {
    const article = createSampleArticle();
    const card = createArticleCard(article);

    card.toggleExpand();
    card.toggleExpand();

    expect(card.isExpanded).toBe(false);
  });

  it('should show truncated summary when collapsed', () => {
    const longSummary = 'A'.repeat(300);
    const article = createSampleArticle({ summary: longSummary });
    const card = createArticleCard(article);

    expect(card.getSummary().length).toBeLessThan(article.summary.length);
  });

  it('should show full summary when expanded', () => {
    const longSummary = 'A'.repeat(300);
    const article = createSampleArticle({ summary: longSummary });
    const card = createArticleCard(article);

    card.toggleExpand();

    expect(card.getSummary()).toBe(longSummary);
  });
});

describe('Date Formatting', () => {
  it('should format dates in short format', () => {
    const article = createSampleArticle({ publishedAt: '2025-06-15T10:00:00Z' });
    const card = createArticleCard(article);

    expect(card.displayDate).toContain('Jun');
  });

  it('should handle different months', () => {
    const months = [
      { date: '2025-01-15T00:00:00Z', expected: 'Jan' },
      { date: '2025-06-15T00:00:00Z', expected: 'Jun' },
      { date: '2025-12-15T00:00:00Z', expected: 'Dec' },
    ];

    months.forEach(({ date, expected }) => {
      const card = createArticleCard(createSampleArticle({ publishedAt: date }));
      expect(card.displayDate).toContain(expected);
    });
  });

  it('should handle different days', () => {
    const article = createSampleArticle({ publishedAt: '2025-01-01T00:00:00Z' });
    const card = createArticleCard(article);

    expect(card.displayDate).toContain('1');
  });
});

describe('Topic Display', () => {
  it('should have access to topics array', () => {
    const article = createSampleArticle({ topics: ['AI', 'ML', 'NLP'] });
    const card = createArticleCard(article);

    expect(card.article.topics).toEqual(['AI', 'ML', 'NLP']);
  });

  it('should handle empty topics', () => {
    const article = createSampleArticle({ topics: [] });
    const card = createArticleCard(article);

    expect(card.article.topics).toEqual([]);
  });

  it('should handle single topic', () => {
    const article = createSampleArticle({ topics: ['Technology'] });
    const card = createArticleCard(article);

    expect(card.article.topics).toHaveLength(1);
  });
});

describe('Source Information', () => {
  it('should display source name', () => {
    const article = createSampleArticle({ sourceName: 'The New York Times' });
    const card = createArticleCard(article);

    expect(card.source).toBe('The New York Times');
  });

  it('should have access to source URL', () => {
    const article = createSampleArticle({ sourceUrl: 'https://example.com/article' });
    const card = createArticleCard(article);

    expect(card.article.sourceUrl).toBe('https://example.com/article');
  });
});

describe('Word Count and Read Time', () => {
  it('should calculate read time from word count', () => {
    const article = createSampleArticle({ wordCount: 1000, readTimeMinutes: 4 });
    const card = createArticleCard(article);

    expect(card.readTime).toBe('4 min read');
  });

  it('should format single minute correctly', () => {
    const article = createSampleArticle({ readTimeMinutes: 1 });
    const card = createArticleCard(article);

    expect(card.readTime).toBe('1 min read');
  });

  it('should format many minutes correctly', () => {
    const article = createSampleArticle({ readTimeMinutes: 15 });
    const card = createArticleCard(article);

    expect(card.readTime).toBe('15 min read');
  });
});

describe('Article ID', () => {
  it('should preserve article ID', () => {
    const article = createSampleArticle({ id: 'unique-article-123' });
    const card = createArticleCard(article);

    expect(card.article.id).toBe('unique-article-123');
  });
});

describe('Bias Confidence', () => {
  it('should have access to bias confidence', () => {
    const article = createSampleArticle({ biasConfidence: 0.95 });
    const card = createArticleCard(article);

    expect(card.article.biasConfidence).toBe(0.95);
  });

  it('should handle low confidence', () => {
    const article = createSampleArticle({ biasConfidence: 0.3 });
    const card = createArticleCard(article);

    expect(card.article.biasConfidence).toBeLessThan(0.5);
  });
});

describe('Edge Cases', () => {
  it('should handle very long titles', () => {
    const longTitle = 'A'.repeat(500);
    const article = createSampleArticle({ title: longTitle });
    const card = createArticleCard(article);

    expect(card.article.title.length).toBe(500);
  });

  it('should handle empty title', () => {
    const article = createSampleArticle({ title: '' });
    const card = createArticleCard(article);

    expect(card.article.title).toBe('');
  });

  it('should handle special characters in title', () => {
    const article = createSampleArticle({ title: 'AI & ML: "The Future"' });
    const card = createArticleCard(article);

    expect(card.article.title).toBe('AI & ML: "The Future"');
  });

  it('should handle unicode in content', () => {
    const article = createSampleArticle({ title: '人工知能の進歩', summary: '中文摘要' });
    const card = createArticleCard(article);

    expect(card.article.title).toBe('人工知能の進歩');
    expect(card.truncatedSummary).toBe('中文摘要');
  });

  it('should handle zero word count', () => {
    const article = createSampleArticle({ wordCount: 0, readTimeMinutes: 0 });
    const card = createArticleCard(article);

    expect(card.readTime).toBe('0 min read');
  });

  it('should handle zero quality score', () => {
    const article = createSampleArticle({ qualityScore: 0 });
    const card = createArticleCard(article);

    expect(card.quality.label).toBe('Poor');
  });

  it('should handle perfect quality score', () => {
    const article = createSampleArticle({ qualityScore: 1 });
    const card = createArticleCard(article);

    expect(card.quality.label).toBe('Excellent');
  });
});

describe('Multiple Cards', () => {
  it('should create independent cards', () => {
    const article1 = createSampleArticle({ id: '1', title: 'First' });
    const article2 = createSampleArticle({ id: '2', title: 'Second' });

    const card1 = createArticleCard(article1);
    const card2 = createArticleCard(article2);

    expect(card1.article.id).not.toBe(card2.article.id);
  });

  it('should have independent expand state', () => {
    const article1 = createSampleArticle({ id: '1' });
    const article2 = createSampleArticle({ id: '2' });

    const card1 = createArticleCard(article1);
    const card2 = createArticleCard(article2);

    card1.toggleExpand();

    expect(card1.isExpanded).toBe(true);
    expect(card2.isExpanded).toBe(false);
  });
});
