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

// Rate limiting configuration
const RATE_LIMIT_CONFIG = {
  maxConcurrent: 2, // Maximum parallel requests
  delayBetweenBatchesMs: 200, // Delay between batches of parallel requests
  maxRetries: 3,
  baseBackoffMs: 1000, // Start with 1 second backoff
  maxTotalRetryMs: 30000, // Maximum total retry time (30 seconds)
};

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
   * @param query - The search query string
   * @param options - Optional search configuration
   * @returns Array of search results
   * @throws {SearchError} If query is invalid (empty, too long) or API request fails
   * @throws {RateLimitError} If API rate limit is exceeded (429 status)
   */
  async search(query: string, options: SearchOptions = {}): Promise<SearchResult[]> {
    // Input validation
    if (!query || typeof query !== 'string') {
      throw new SearchError('Query must be a non-empty string', 400);
    }
    const trimmedQuery = query.trim();
    if (trimmedQuery.length === 0) {
      throw new SearchError('Query cannot be empty or whitespace only', 400);
    }
    if (trimmedQuery.length > 1000) {
      throw new SearchError('Query exceeds maximum length of 1000 characters', 400);
    }

    const {
      maxResults = 10,
      searchDepth = 'advanced',
      includeDomains,
      excludeDomains,
      daysBack,
    } = options;

    // Validate maxResults bounds
    const validatedMaxResults = Math.min(Math.max(1, maxResults), 100);

    const startTime = Date.now();

    const payload: Record<string, unknown> = {
      api_key: this.apiKey,
      query: trimmedQuery,
      max_results: validatedMaxResults,
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

        // Throw RateLimitError for 429 status to enable retry logic
        if (response.status === 429) {
          const retryAfter = response.headers.get('Retry-After');
          throw new RateLimitError(
            `Tavily API rate limit: ${errorText}`,
            retryAfter ? parseFloat(retryAfter) : undefined
          );
        }

        throw new SearchError(
          `Tavily API error (${response.status}): ${errorText}`,
          response.status
        );
      }

      const rawData = await response.json();
      const data = validateTavilyResponse(rawData);
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
   * Uses rate limiting and retry logic to handle API limits gracefully.
   * @param topicName - The topic to search for
   * @param keywords - Keywords to include in the search
   * @param options - Optional search configuration including excludeKeywords and preferPremiumSources
   * @returns Array of unique, deduplicated search results sorted by relevance
   */
  async searchTopic(
    topicName: string,
    keywords: string[],
    options: SearchOptions & { excludeKeywords?: string[]; preferPremiumSources?: boolean } = {}
  ): Promise<SearchResult[]> {
    const { excludeKeywords, preferPremiumSources = true, maxResults = 15, ...searchOptions } = options;

    // Generate search queries
    const queries = this.generateTopicQueries(topicName, keywords, excludeKeywords);

    // Execute searches with rate limiting and concurrency control
    // Uses a middle ground: run up to 2 queries in parallel, with delays between batches
    const resultsPerQuery = Math.ceil(maxResults / Math.min(queries.length, 3)) + 5;
    const queriesToExecute = queries.slice(0, 3);

    const resultsLists: SearchResult[][] = [];
    for (let i = 0; i < queriesToExecute.length; i += RATE_LIMIT_CONFIG.maxConcurrent) {
      // Add delay between batches to avoid rate limits
      if (i > 0) {
        await this.delay(RATE_LIMIT_CONFIG.delayBetweenBatchesMs);
      }

      // Run batch of queries in parallel
      const batch = queriesToExecute.slice(i, i + RATE_LIMIT_CONFIG.maxConcurrent);
      const batchPromises = batch.map((query) =>
        this.searchWithRetry(query, {
          ...searchOptions,
          maxResults: resultsPerQuery,
        })
      );
      const batchResults = await Promise.all(batchPromises);
      resultsLists.push(...batchResults);
    }

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
   * Delay execution for specified milliseconds.
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Search with exponential backoff retry for rate limit errors.
   * Includes timeout protection to prevent excessive delays.
   */
  private async searchWithRetry(
    query: string,
    options: SearchOptions
  ): Promise<SearchResult[]> {
    let lastError: Error | null = null;
    const retryStartTime = Date.now();

    for (let attempt = 0; attempt < RATE_LIMIT_CONFIG.maxRetries; attempt++) {
      // Check if total retry time exceeded
      if (Date.now() - retryStartTime > RATE_LIMIT_CONFIG.maxTotalRetryMs) {
        console.error(
          `Retry timeout exceeded for query "${query}" after ${Date.now() - retryStartTime}ms`
        );
        return [];
      }

      try {
        return await this.search(query, options);
      } catch (err) {
        lastError = err instanceof Error ? err : new Error(String(err));

        // Retry on rate limit errors (429) - check both error type and status code for safety
        const isRateLimitError =
          err instanceof RateLimitError ||
          (err instanceof SearchError && err.statusCode === 429);

        if (isRateLimitError) {
          const backoffMs =
            err instanceof RateLimitError && err.retryAfter
              ? err.retryAfter * 1000
              : RATE_LIMIT_CONFIG.baseBackoffMs * Math.pow(2, attempt);

          console.warn(
            `Rate limited on query "${query}", retrying in ${backoffMs}ms (attempt ${attempt + 1}/${RATE_LIMIT_CONFIG.maxRetries})`
          );
          await this.delay(backoffMs);
        } else {
          // Don't retry other errors
          const errorDetails = {
            message: lastError.message,
            name: lastError.name,
            statusCode: (err as SearchError).statusCode,
          };
          console.error(`Search query failed: ${query}`, JSON.stringify(errorDetails));
          return [];
        }
      }
    }

    // All retries exhausted
    console.error(
      `Search query failed after ${RATE_LIMIT_CONFIG.maxRetries} retries: ${query}`,
      lastError?.message
    );
    return [];
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

/**
 * Runtime validation for Tavily API response.
 * Validates critical fields to catch API changes early.
 */
function validateTavilyResponse(data: unknown): TavilyResponse {
  if (!data || typeof data !== 'object') {
    throw new SearchError('Invalid Tavily response: expected object', 0);
  }

  const response = data as Record<string, unknown>;

  if (!Array.isArray(response.results)) {
    throw new SearchError('Invalid Tavily response: missing or invalid results array', 0);
  }

  // Validate each result has required fields
  for (let i = 0; i < response.results.length; i++) {
    const result = response.results[i] as Record<string, unknown>;
    if (!result || typeof result !== 'object') {
      throw new SearchError(`Invalid Tavily response: invalid result at index ${i}`, 0);
    }
    if (typeof result.url !== 'string') {
      throw new SearchError(`Invalid Tavily response: missing url at index ${i}`, 0);
    }
    if (typeof result.title !== 'string') {
      throw new SearchError(`Invalid Tavily response: missing title at index ${i}`, 0);
    }
  }

  return data as TavilyResponse;
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
