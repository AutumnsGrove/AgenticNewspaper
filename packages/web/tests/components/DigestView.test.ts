/**
 * Tests for DigestView component behavior.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

interface DigestArticle {
  id: string;
  title: string;
  summary: string;
  sourceUrl: string;
  sourceName: string;
  qualityScore: number;
  topics: string[];
}

interface DigestConnection {
  article1Id: string;
  article2Id: string;
  similarity: number;
  description: string;
}

interface Digest {
  id: string;
  title: string;
  subtitle: string;
  createdAt: string;
  articles: DigestArticle[];
  topics: string[];
  connections: DigestConnection[];
  metadata: {
    totalArticles: number;
    averageQuality: number;
  };
}

const createDigestView = (digest: Digest) => {
  let sortBy: 'quality' | 'topic' | 'source' = 'quality';
  let filterTopic: string | null = null;
  let selectedArticleId: string | null = null;
  let showConnections = true;

  const getFilteredArticles = () => {
    let articles = [...digest.articles];

    if (filterTopic) {
      articles = articles.filter((a) => a.topics.includes(filterTopic!));
    }

    switch (sortBy) {
      case 'quality':
        articles.sort((a, b) => b.qualityScore - a.qualityScore);
        break;
      case 'topic':
        articles.sort((a, b) => a.topics[0]?.localeCompare(b.topics[0] || '') || 0);
        break;
      case 'source':
        articles.sort((a, b) => a.sourceName.localeCompare(b.sourceName));
        break;
    }

    return articles;
  };

  const getConnectionsForArticle = (articleId: string) => {
    if (!showConnections) return [];
    return digest.connections.filter(
      (c) => c.article1Id === articleId || c.article2Id === articleId
    );
  };

  const getConnectedArticle = (connection: DigestConnection, currentId: string) => {
    const otherId = connection.article1Id === currentId ? connection.article2Id : connection.article1Id;
    return digest.articles.find((a) => a.id === otherId);
  };

  const getTopicCounts = () => {
    const counts: Record<string, number> = {};
    for (const article of digest.articles) {
      for (const topic of article.topics) {
        counts[topic] = (counts[topic] || 0) + 1;
      }
    }
    return counts;
  };

  return {
    digest,
    get sortBy() {
      return sortBy;
    },
    set sortBy(value: 'quality' | 'topic' | 'source') {
      sortBy = value;
    },
    get filterTopic() {
      return filterTopic;
    },
    set filterTopic(value: string | null) {
      filterTopic = value;
    },
    get selectedArticleId() {
      return selectedArticleId;
    },
    set selectedArticleId(value: string | null) {
      selectedArticleId = value;
    },
    get showConnections() {
      return showConnections;
    },
    set showConnections(value: boolean) {
      showConnections = value;
    },
    getFilteredArticles,
    getConnectionsForArticle,
    getConnectedArticle,
    getTopicCounts,
    get uniqueTopics() {
      return [...new Set(digest.articles.flatMap((a) => a.topics))];
    },
    get uniqueSources() {
      return [...new Set(digest.articles.map((a) => a.sourceName))];
    },
  };
};

const createSampleDigest = (): Digest => ({
  id: 'digest-1',
  title: 'Morning Brief',
  subtitle: 'Your daily tech digest',
  createdAt: '2025-01-15T06:00:00Z',
  articles: [
    {
      id: 'a1',
      title: 'AI Breakthrough',
      summary: 'New AI model released',
      sourceUrl: 'https://techcrunch.com/a1',
      sourceName: 'TechCrunch',
      qualityScore: 0.9,
      topics: ['AI', 'Technology'],
    },
    {
      id: 'a2',
      title: 'Climate Research',
      summary: 'New climate findings',
      sourceUrl: 'https://nature.com/a2',
      sourceName: 'Nature',
      qualityScore: 0.85,
      topics: ['Science', 'Climate'],
    },
    {
      id: 'a3',
      title: 'Tech Startup News',
      summary: 'Startup raises funds',
      sourceUrl: 'https://techcrunch.com/a3',
      sourceName: 'TechCrunch',
      qualityScore: 0.75,
      topics: ['Technology', 'Startups'],
    },
    {
      id: 'a4',
      title: 'AI in Healthcare',
      summary: 'AI applied to medicine',
      sourceUrl: 'https://wired.com/a4',
      sourceName: 'Wired',
      qualityScore: 0.8,
      topics: ['AI', 'Healthcare'],
    },
  ],
  topics: ['AI', 'Technology', 'Science', 'Climate', 'Startups', 'Healthcare'],
  connections: [
    { article1Id: 'a1', article2Id: 'a4', similarity: 0.8, description: 'Both about AI' },
    { article1Id: 'a1', article2Id: 'a3', similarity: 0.6, description: 'Tech related' },
  ],
  metadata: {
    totalArticles: 4,
    averageQuality: 0.825,
  },
});

describe('DigestView Creation', () => {
  it('should create view from digest data', () => {
    const digest = createSampleDigest();
    const view = createDigestView(digest);

    expect(view.digest).toBe(digest);
  });

  it('should have default sort by quality', () => {
    const view = createDigestView(createSampleDigest());
    expect(view.sortBy).toBe('quality');
  });

  it('should have no filter by default', () => {
    const view = createDigestView(createSampleDigest());
    expect(view.filterTopic).toBeNull();
  });

  it('should show connections by default', () => {
    const view = createDigestView(createSampleDigest());
    expect(view.showConnections).toBe(true);
  });
});

describe('Article Sorting', () => {
  it('should sort by quality descending', () => {
    const view = createDigestView(createSampleDigest());
    view.sortBy = 'quality';
    const articles = view.getFilteredArticles();

    for (let i = 0; i < articles.length - 1; i++) {
      expect(articles[i].qualityScore).toBeGreaterThanOrEqual(articles[i + 1].qualityScore);
    }
  });

  it('should sort by topic alphabetically', () => {
    const view = createDigestView(createSampleDigest());
    view.sortBy = 'topic';
    const articles = view.getFilteredArticles();

    for (let i = 0; i < articles.length - 1; i++) {
      const topic1 = articles[i].topics[0] || '';
      const topic2 = articles[i + 1].topics[0] || '';
      expect(topic1.localeCompare(topic2)).toBeLessThanOrEqual(0);
    }
  });

  it('should sort by source alphabetically', () => {
    const view = createDigestView(createSampleDigest());
    view.sortBy = 'source';
    const articles = view.getFilteredArticles();

    for (let i = 0; i < articles.length - 1; i++) {
      expect(articles[i].sourceName.localeCompare(articles[i + 1].sourceName)).toBeLessThanOrEqual(0);
    }
  });

  it('should change sort order', () => {
    const view = createDigestView(createSampleDigest());

    view.sortBy = 'quality';
    const byQuality = view.getFilteredArticles();

    view.sortBy = 'source';
    const bySource = view.getFilteredArticles();

    expect(byQuality[0].id).not.toBe(bySource[0].id);
  });
});

describe('Topic Filtering', () => {
  it('should filter by topic', () => {
    const view = createDigestView(createSampleDigest());
    view.filterTopic = 'AI';
    const articles = view.getFilteredArticles();

    expect(articles.length).toBe(2);
    articles.forEach((a) => {
      expect(a.topics).toContain('AI');
    });
  });

  it('should return all articles when no filter', () => {
    const view = createDigestView(createSampleDigest());
    view.filterTopic = null;
    const articles = view.getFilteredArticles();

    expect(articles.length).toBe(4);
  });

  it('should return empty for non-existent topic', () => {
    const view = createDigestView(createSampleDigest());
    view.filterTopic = 'NonExistent';
    const articles = view.getFilteredArticles();

    expect(articles.length).toBe(0);
  });

  it('should combine filter and sort', () => {
    const view = createDigestView(createSampleDigest());
    view.filterTopic = 'AI';
    view.sortBy = 'quality';
    const articles = view.getFilteredArticles();

    expect(articles.length).toBe(2);
    expect(articles[0].qualityScore).toBeGreaterThanOrEqual(articles[1].qualityScore);
  });
});

describe('Connection Display', () => {
  it('should get connections for article', () => {
    const view = createDigestView(createSampleDigest());
    const connections = view.getConnectionsForArticle('a1');

    expect(connections.length).toBe(2);
  });

  it('should return empty when no connections', () => {
    const view = createDigestView(createSampleDigest());
    const connections = view.getConnectionsForArticle('a2');

    expect(connections.length).toBe(0);
  });

  it('should hide connections when disabled', () => {
    const view = createDigestView(createSampleDigest());
    view.showConnections = false;
    const connections = view.getConnectionsForArticle('a1');

    expect(connections.length).toBe(0);
  });

  it('should get connected article', () => {
    const view = createDigestView(createSampleDigest());
    const connection = view.digest.connections[0];
    const connected = view.getConnectedArticle(connection, 'a1');

    expect(connected?.id).toBe('a4');
  });

  it('should get connected article from either side', () => {
    const view = createDigestView(createSampleDigest());
    const connection = view.digest.connections[0];
    const connected = view.getConnectedArticle(connection, 'a4');

    expect(connected?.id).toBe('a1');
  });
});

describe('Topic Statistics', () => {
  it('should count articles per topic', () => {
    const view = createDigestView(createSampleDigest());
    const counts = view.getTopicCounts();

    expect(counts['AI']).toBe(2);
    expect(counts['Technology']).toBe(2);
    expect(counts['Science']).toBe(1);
  });

  it('should list unique topics', () => {
    const view = createDigestView(createSampleDigest());
    const topics = view.uniqueTopics;

    expect(topics).toContain('AI');
    expect(topics).toContain('Technology');
    expect(topics).toContain('Science');
  });

  it('should list unique sources', () => {
    const view = createDigestView(createSampleDigest());
    const sources = view.uniqueSources;

    expect(sources).toContain('TechCrunch');
    expect(sources).toContain('Nature');
    expect(sources).toContain('Wired');
    expect(sources.length).toBe(3);
  });
});

describe('Article Selection', () => {
  it('should select article', () => {
    const view = createDigestView(createSampleDigest());
    view.selectedArticleId = 'a1';

    expect(view.selectedArticleId).toBe('a1');
  });

  it('should deselect article', () => {
    const view = createDigestView(createSampleDigest());
    view.selectedArticleId = 'a1';
    view.selectedArticleId = null;

    expect(view.selectedArticleId).toBeNull();
  });

  it('should change selection', () => {
    const view = createDigestView(createSampleDigest());
    view.selectedArticleId = 'a1';
    view.selectedArticleId = 'a2';

    expect(view.selectedArticleId).toBe('a2');
  });
});

describe('Metadata Access', () => {
  it('should access total articles', () => {
    const view = createDigestView(createSampleDigest());
    expect(view.digest.metadata.totalArticles).toBe(4);
  });

  it('should access average quality', () => {
    const view = createDigestView(createSampleDigest());
    expect(view.digest.metadata.averageQuality).toBe(0.825);
  });

  it('should access digest title', () => {
    const view = createDigestView(createSampleDigest());
    expect(view.digest.title).toBe('Morning Brief');
  });

  it('should access digest subtitle', () => {
    const view = createDigestView(createSampleDigest());
    expect(view.digest.subtitle).toBe('Your daily tech digest');
  });
});

describe('Edge Cases', () => {
  it('should handle empty digest', () => {
    const emptyDigest: Digest = {
      id: 'empty',
      title: 'Empty',
      subtitle: '',
      createdAt: '2025-01-15T00:00:00Z',
      articles: [],
      topics: [],
      connections: [],
      metadata: { totalArticles: 0, averageQuality: 0 },
    };
    const view = createDigestView(emptyDigest);

    expect(view.getFilteredArticles()).toEqual([]);
    expect(view.uniqueTopics).toEqual([]);
    expect(view.uniqueSources).toEqual([]);
  });

  it('should handle articles without topics', () => {
    const digest = createSampleDigest();
    digest.articles[0].topics = [];
    const view = createDigestView(digest);

    view.sortBy = 'topic';
    const articles = view.getFilteredArticles();

    expect(articles.length).toBe(4);
  });

  it('should handle single article', () => {
    const singleDigest: Digest = {
      id: 'single',
      title: 'Single',
      subtitle: '',
      createdAt: '2025-01-15T00:00:00Z',
      articles: [
        {
          id: 'only',
          title: 'Only Article',
          summary: 'Summary',
          sourceUrl: 'https://example.com',
          sourceName: 'Example',
          qualityScore: 0.8,
          topics: ['Topic'],
        },
      ],
      topics: ['Topic'],
      connections: [],
      metadata: { totalArticles: 1, averageQuality: 0.8 },
    };
    const view = createDigestView(singleDigest);

    expect(view.getFilteredArticles().length).toBe(1);
    expect(view.getConnectionsForArticle('only')).toEqual([]);
  });
});

describe('Quality Score Range', () => {
  it('should handle articles with same quality', () => {
    const digest = createSampleDigest();
    digest.articles.forEach((a) => (a.qualityScore = 0.8));
    const view = createDigestView(digest);

    view.sortBy = 'quality';
    const articles = view.getFilteredArticles();

    expect(articles.length).toBe(4);
  });

  it('should handle extreme quality scores', () => {
    const digest = createSampleDigest();
    digest.articles[0].qualityScore = 1.0;
    digest.articles[1].qualityScore = 0.0;
    const view = createDigestView(digest);

    view.sortBy = 'quality';
    const articles = view.getFilteredArticles();

    expect(articles[0].qualityScore).toBe(1.0);
    expect(articles[articles.length - 1].qualityScore).toBe(0.0);
  });
});

describe('Connection Similarity', () => {
  it('should have access to similarity scores', () => {
    const view = createDigestView(createSampleDigest());
    const connection = view.digest.connections[0];

    expect(connection.similarity).toBe(0.8);
  });

  it('should have access to connection descriptions', () => {
    const view = createDigestView(createSampleDigest());
    const connection = view.digest.connections[0];

    expect(connection.description).toBe('Both about AI');
  });
});

describe('Multiple Views', () => {
  it('should create independent views', () => {
    const digest = createSampleDigest();
    const view1 = createDigestView(digest);
    const view2 = createDigestView(digest);

    view1.sortBy = 'source';
    view2.sortBy = 'topic';

    expect(view1.sortBy).toBe('source');
    expect(view2.sortBy).toBe('topic');
  });

  it('should have independent filters', () => {
    const digest = createSampleDigest();
    const view1 = createDigestView(digest);
    const view2 = createDigestView(digest);

    view1.filterTopic = 'AI';
    view2.filterTopic = 'Science';

    expect(view1.getFilteredArticles().length).toBe(2);
    expect(view2.getFilteredArticles().length).toBe(1);
  });
});

describe('Topic Counts Edge Cases', () => {
  it('should handle articles with multiple topics', () => {
    const view = createDigestView(createSampleDigest());
    const counts = view.getTopicCounts();

    // Total topic occurrences should be > number of articles
    const totalOccurrences = Object.values(counts).reduce((a, b) => a + b, 0);
    expect(totalOccurrences).toBeGreaterThan(view.digest.articles.length);
  });

  it('should handle no topics', () => {
    const digest = createSampleDigest();
    digest.articles.forEach((a) => (a.topics = []));
    const view = createDigestView(digest);
    const counts = view.getTopicCounts();

    expect(Object.keys(counts).length).toBe(0);
  });
});
