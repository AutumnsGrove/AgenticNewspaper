/**
 * Search Service - Tavily integration for article discovery.
 *
 * Ported from Python: packages/core/src/services/search.py
 * Uses Tavily API for AI-focused search with quality results.
 */

import type { Env } from '../types';

// ============================================================================
// Types
// ============================================================================

export interface SearchResult {
  url: string;
  title: string;
  snippet: string;
  source: string;
  publishedDate?: string;
  relevanceScore: number;
  rank: number;
  rawContent?: string;
}

export interface SearchOptions {
  maxResults?: number;
  searchDepth?: 'basic' | 'advanced';
  includeDomains?: string[];
  excludeDomains?: string[];
  daysBack?: number;
}

export interface SearchStats {
  totalSearches: number;
  totalResults: number;
  totalTimeMs: number;
  errors: number;
}

// ============================================================================
// Constants
// ============================================================================

const TAVILY_BASE_URL = 'https://api.tavily.com';

const PREMIUM_SOURCES = [
  'arxiv.org',
  'nature.com',
  'science.org',
  'arstechnica.com',
  'wired.com',
  'techcrunch.com',
  'theverge.com',
  'news.ycombinator.com',
  'github.com',
  'openai.com',
  'anthropic.com',
  'deepmind.com',
  'mit.edu',
  'stanford.edu',
  'acm.org',
  'ieee.org',
];

// ============================================================================
// Search Service
// ============================================================================

export class SearchService {
  private apiKey: string;
  private stats: SearchStats = {
    totalSearches: 0,
    totalResults: 0,
    totalTimeMs: 0,
    errors: 0,
  };

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  /**
   * Create SearchService from environment.
   */
  static fromEnv(env: Env): SearchService {
    const apiKey = env.TAVILY_API_KEY;
    if (!apiKey) {
      throw new Error('TAVILY_API_KEY not configured');
    }
    return new SearchService(apiKey);
  }

  /**
   * Search for articles matching query.
   */
  async search(query: string, options: SearchOptions = {}): Promise<SearchResult[]> {
    const {
      maxResults = 10,
      searchDepth = 'advanced',
      includeDomains,
      excludeDomains,
      daysBack,
    } = options;

    const startTime = Date.now();

    const payload: Record<string, unknown> = {
      api_key: this.apiKey,
      query,
      max_results: maxResults,
      search_depth: searchDepth,
      include_answer: false,
      include_raw_content: false,
      include_images: false,
    };

    if (includeDomains && includeDomains.length > 0) {
      payload.include_domains = includeDomains;
    }
    if (excludeDomains && excludeDomains.length > 0) {
      payload.exclude_domains = excludeDomains;
    }
    if (daysBack) {
      payload.days = daysBack;
    }

    try {
      const response = await fetch(`${TAVILY_BASE_URL}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorText = await response.text();
        this.stats.errors++;
        throw new SearchError(
          `Tavily API error (${response.status}): ${errorText}`,
          response.status
        );
      }

      const data = (await response.json()) as TavilyResponse;
      const results = this.parseResults(data);

      // Update stats
      const elapsed = Date.now() - startTime;
      this.stats.totalSearches++;
      this.stats.totalResults += results.length;
      this.stats.totalTimeMs += elapsed;

      return results;
    } catch (error) {
      if (error instanceof SearchError) {
        throw error;
      }
      this.stats.errors++;
      throw new SearchError(
        `Search failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        0
      );
    }
  }

  /**
   * Search for articles on a specific topic with multiple queries.
   */
  async searchTopic(
    topicName: string,
    keywords: string[],
    options: SearchOptions & { excludeKeywords?: string[]; preferPremiumSources?: boolean } = {}
  ): Promise<SearchResult[]> {
    const { excludeKeywords, preferPremiumSources = true, maxResults = 15, ...searchOptions } = options;

    // Generate search queries
    const queries = this.generateTopicQueries(topicName, keywords, excludeKeywords);

    // Execute searches (limit to 3 to avoid rate limits)
    const resultsPerQuery = Math.ceil(maxResults / Math.min(queries.length, 3)) + 5;
    const searchPromises = queries.slice(0, 3).map((query) =>
      this.search(query, { ...searchOptions, maxResults: resultsPerQuery }).catch((err) => {
        console.error(`Search query failed: ${query}`, err);
        return [] as SearchResult[];
      })
    );

    const resultsLists = await Promise.all(searchPromises);

    // Flatten and deduplicate by URL
    const seenUrls = new Set<string>();
    const uniqueResults: SearchResult[] = [];

    for (const results of resultsLists) {
      for (const result of results) {
        if (!seenUrls.has(result.url)) {
          seenUrls.add(result.url);
          uniqueResults.push(result);
        }
      }
    }

    // Boost premium sources
    if (preferPremiumSources) {
      for (const result of uniqueResults) {
        if (PREMIUM_SOURCES.some((source) => result.url.includes(source))) {
          result.relevanceScore = Math.min(1.0, result.relevanceScore + 0.15);
        }
      }
    }

    // Sort by relevance
    uniqueResults.sort((a, b) => b.relevanceScore - a.relevanceScore);

    return uniqueResults.slice(0, maxResults);
  }

  /**
   * Generate search queries for a topic.
   */
  private generateTopicQueries(
    topicName: string,
    keywords: string[],
    excludeKeywords?: string[]
  ): string[] {
    const queries: string[] = [];

    // Primary query with topic and top keywords
    let primary = `${topicName} ${keywords.slice(0, 3).join(' ')}`;
    if (excludeKeywords && excludeKeywords.length > 0) {
      primary += ' -' + excludeKeywords.slice(0, 2).join(' -');
    }
    queries.push(primary);

    // Alternative query focusing on recent news
    if (keywords.length > 0) {
      queries.push(`latest ${keywords[0]} news ${topicName.split(' ')[0]}`);
    }

    // Technical/research focused query
    const techTopics = ['ai', 'ml', 'machine learning', 'science'];
    if (techTopics.some((t) => topicName.toLowerCase().includes(t))) {
      queries.push(`research paper ${keywords.slice(0, 2).join(' ')}`);
    }

    return queries;
  }

  /**
   * Parse Tavily response into SearchResult array.
   */
  private parseResults(data: TavilyResponse): SearchResult[] {
    const results: SearchResult[] = [];

    for (let i = 0; i < (data.results || []).length; i++) {
      const item = data.results[i];

      results.push({
        url: item.url || '',
        title: item.title || '',
        snippet: item.content || item.snippet || '',
        source: this.extractSource(item.url || ''),
        publishedDate: item.published_date,
        relevanceScore: item.score || 0,
        rank: i + 1,
        rawContent: item.raw_content,
      });
    }

    return results;
  }

  /**
   * Extract source domain from URL.
   */
  private extractSource(url: string): string {
    try {
      const parsed = new URL(url);
      return parsed.hostname.replace('www.', '');
    } catch {
      return 'unknown';
    }
  }

  /**
   * Get search statistics.
   */
  getStats(): SearchStats {
    return { ...this.stats };
  }

  /**
   * Reset statistics.
   */
  resetStats(): void {
    this.stats = {
      totalSearches: 0,
      totalResults: 0,
      totalTimeMs: 0,
      errors: 0,
    };
  }
}

// ============================================================================
// Tavily API Types
// ============================================================================

interface TavilyResponse {
  results: TavilyResult[];
  answer?: string;
  query?: string;
}

interface TavilyResult {
  url: string;
  title: string;
  content?: string;
  snippet?: string;
  score: number;
  published_date?: string;
  raw_content?: string;
}

// ============================================================================
// Error Types
// ============================================================================

export class SearchError extends Error {
  statusCode: number;

  constructor(message: string, statusCode: number) {
    super(message);
    this.name = 'SearchError';
    this.statusCode = statusCode;
  }
}

export class RateLimitError extends SearchError {
  retryAfter?: number;

  constructor(message: string, retryAfter?: number) {
    super(message, 429);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}
