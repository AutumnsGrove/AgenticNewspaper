/**
 * Parser Service - Article content extraction.
 *
 * Ported from Python: packages/core/src/agents/tier1_execution/parser_agent.py
 * Uses simple regex-based extraction for Cloudflare Workers compatibility.
 * Can optionally use LLM for more accurate extraction.
 */

import type { Env } from '../types';
import { LLMService } from './llm';

// ============================================================================
// Types
// ============================================================================

export interface ParsedArticle {
  articleId: string;
  url: string;
  title: string;
  content: string;
  author?: string;
  publishedDate?: string;
  source: string;
  wordCount: number;
  readingTimeMinutes: number;
  contentPreview: string;
  parseQuality: number;
}

export interface ParserOptions {
  useLLM?: boolean;
  maxContentLength?: number;
  timeout?: number;
}

export interface ParserStats {
  parseCount: number;
  successCount: number;
  failureCount: number;
  totalTimeMs: number;
}

// ============================================================================
// Parser Service
// ============================================================================

export class ParserService {
  private llm?: LLMService;
  private stats: ParserStats = {
    parseCount: 0,
    successCount: 0,
    failureCount: 0,
    totalTimeMs: 0,
  };

  constructor(llm?: LLMService) {
    this.llm = llm;
  }

  /**
   * Create ParserService from environment.
   */
  static fromEnv(env: Env): ParserService {
    let llm: LLMService | undefined;
    if (env.OPENROUTER_API_KEY) {
      llm = LLMService.fromEnv(env);
    }
    return new ParserService(llm);
  }

  /**
   * Validate URL format.
   */
  private isValidUrl(url: string): boolean {
    try {
      const parsed = new URL(url);
      return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch {
      return false;
    }
  }

  /**
   * Parse article from URL.
   */
  async parseArticle(
    url: string,
    expectedTitle: string,
    source: string,
    options: ParserOptions = {}
  ): Promise<ParsedArticle | null> {
    // Input validation
    if (!url || typeof url !== 'string') {
      console.error('Parse error: URL must be a non-empty string');
      return null;
    }
    if (!this.isValidUrl(url)) {
      console.error(`Parse error: Invalid URL format: ${url}`);
      return null;
    }

    const { useLLM = false, maxContentLength = 10000, timeout = 30000 } = options;

    const startTime = Date.now();
    this.stats.parseCount++;

    try {
      // Fetch HTML content
      const html = await this.fetchWithTimeout(url, timeout);
      if (!html) {
        this.stats.failureCount++;
        return null;
      }

      // Extract content
      let extracted: ExtractedContent;
      if (useLLM && this.llm) {
        extracted = await this.extractWithLLM(html, url, expectedTitle);
      } else {
        extracted = this.extractWithRegex(html, expectedTitle);
      }

      // Truncate content if needed
      let content = extracted.content;
      if (content.length > maxContentLength) {
        content = content.substring(0, maxContentLength) + '\n\n[Content truncated]';
      }

      // Calculate metrics
      const wordCount = this.countWords(content);
      const readingTime = Math.ceil(wordCount / 200); // ~200 wpm reading speed
      const parseQuality = this.assessQuality(extracted, content);

      // Generate article ID
      const articleId = this.generateArticleId(url);

      const article: ParsedArticle = {
        articleId,
        url,
        title: extracted.title || expectedTitle,
        content,
        author: extracted.author,
        publishedDate: extracted.publishedDate,
        source,
        wordCount,
        readingTimeMinutes: readingTime,
        contentPreview: content.substring(0, 200).trim() + '...',
        parseQuality,
      };

      this.stats.successCount++;
      this.stats.totalTimeMs += Date.now() - startTime;

      return article;
    } catch (error) {
      // Limit stack trace exposure in production for security
      const isProduction = typeof process !== 'undefined' && process.env?.NODE_ENV === 'production';
      const errorDetails = {
        url,
        expectedTitle,
        source,
        error: error instanceof Error
          ? {
              name: error.name,
              message: error.message,
              ...(isProduction ? {} : { stack: error.stack?.split('\n').slice(0, 3).join('\n') }),
            }
          : String(error),
        parseTimeMs: Date.now() - startTime,
      };
      console.error(`Parse error:`, JSON.stringify(errorDetails));
      this.stats.failureCount++;
      this.stats.totalTimeMs += Date.now() - startTime;
      return null;
    }
  }

  /**
   * Parse multiple articles in parallel.
   */
  async parseArticles(
    articles: Array<{ url: string; title: string; source: string }>,
    options: ParserOptions & { maxConcurrent?: number } = {}
  ): Promise<Array<ParsedArticle | null>> {
    const { maxConcurrent = 5, ...parserOptions } = options;

    // Process in batches to limit concurrency
    const results: Array<ParsedArticle | null> = [];
    for (let i = 0; i < articles.length; i += maxConcurrent) {
      const batch = articles.slice(i, i + maxConcurrent);
      const batchResults = await Promise.all(
        batch.map((article) =>
          this.parseArticle(article.url, article.title, article.source, parserOptions)
        )
      );
      results.push(...batchResults);
    }

    return results;
  }

  /**
   * Fetch URL with timeout.
   */
  private async fetchWithTimeout(url: string, timeout: number): Promise<string | null> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        signal: controller.signal,
        headers: {
          'User-Agent':
            'Mozilla/5.0 (compatible; TheDailyClearing/1.0; +https://clearing.autumnsgrove.com)',
          Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        console.error(`Fetch failed for ${url}: ${response.status}`);
        return null;
      }

      return await response.text();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        console.error(`Fetch timeout for ${url}`);
      }
      return null;
    }
  }

  /**
   * Extract content using regex patterns.
   */
  private extractWithRegex(html: string, expectedTitle: string): ExtractedContent {
    const result: ExtractedContent = {
      title: expectedTitle,
      content: '',
    };

    // Extract title from various sources
    const titleMatch =
      html.match(/<title[^>]*>([^<]+)<\/title>/i) ||
      html.match(/<h1[^>]*>([^<]+)<\/h1>/i) ||
      html.match(/<meta[^>]*property="og:title"[^>]*content="([^"]+)"/i);
    if (titleMatch) {
      result.title = this.decodeHtmlEntities(titleMatch[1].trim());
    }

    // Extract author
    const authorMatch =
      html.match(/<meta[^>]*name="author"[^>]*content="([^"]+)"/i) ||
      html.match(/class="(?:author|byline)[^"]*"[^>]*>([^<]+)</i) ||
      html.match(/rel="author"[^>]*>([^<]+)</i);
    if (authorMatch) {
      result.author = this.decodeHtmlEntities(authorMatch[1].trim());
    }

    // Extract published date
    const dateMatch =
      html.match(/<meta[^>]*property="article:published_time"[^>]*content="([^"]+)"/i) ||
      html.match(/<time[^>]*datetime="([^"]+)"/i) ||
      html.match(/class="(?:date|published|time)[^"]*"[^>]*>([^<]+)</i);
    if (dateMatch) {
      result.publishedDate = dateMatch[1].trim();
    }

    // Extract main content using multiple strategies
    let content = '';

    // Strategy 1: Look for article tag
    const articleMatch = html.match(/<article[^>]*>([\s\S]*?)<\/article>/i);
    if (articleMatch) {
      content = articleMatch[1];
    }

    // Strategy 2: Look for main content div
    if (!content || content.length < 500) {
      const mainMatch =
        html.match(/<main[^>]*>([\s\S]*?)<\/main>/i) ||
        html.match(/class="(?:content|post-content|article-body|entry-content)[^"]*"[^>]*>([\s\S]*?)<\/div>/i);
      if (mainMatch && mainMatch[1].length > content.length) {
        content = mainMatch[1];
      }
    }

    // Strategy 3: Extract all paragraphs
    if (!content || content.length < 500) {
      const paragraphs: string[] = [];
      const pRegex = /<p[^>]*>([\s\S]*?)<\/p>/gi;
      let match;
      while ((match = pRegex.exec(html)) !== null) {
        const text = this.stripHtml(match[1]).trim();
        if (text.length > 50) {
          // Skip very short paragraphs
          paragraphs.push(text);
        }
      }
      if (paragraphs.length > 0) {
        content = paragraphs.join('\n\n');
      }
    }

    // Clean and format content
    result.content = this.cleanContent(content);

    return result;
  }

  /**
   * Extract content using LLM for better accuracy.
   */
  private async extractWithLLM(
    html: string,
    url: string,
    expectedTitle: string
  ): Promise<ExtractedContent> {
    if (!this.llm) {
      return this.extractWithRegex(html, expectedTitle);
    }

    // Truncate HTML to fit in context
    const htmlPreview = html.substring(0, 4000);

    const prompt = `Extract the main article content from this HTML:

URL: ${url}
Expected title: ${expectedTitle}

HTML:
${htmlPreview}

Extract and return in this format:
TITLE: [article title]
AUTHOR: [author name or "Unknown"]
CONTENT: [main article text, no HTML tags, preserve paragraphs with double newlines]

Focus on the main article content, ignore navigation, ads, and sidebars.`;

    try {
      const response = await this.llm.complete(prompt, {
        maxTokens: 2000,
        temperature: 0.1,
      });

      return this.parseLLMResponse(response.content, expectedTitle);
    } catch (error) {
      console.error('LLM extraction failed, falling back to regex:', error);
      return this.extractWithRegex(html, expectedTitle);
    }
  }

  /**
   * Parse LLM extraction response.
   */
  private parseLLMResponse(response: string, defaultTitle: string): ExtractedContent {
    const result: ExtractedContent = {
      title: defaultTitle,
      content: '',
    };

    const lines = response.split('\n');
    let currentField: 'content' | null = null;

    for (const line of lines) {
      const trimmed = line.trim();

      if (trimmed.startsWith('TITLE:')) {
        result.title = trimmed.substring(6).trim();
        currentField = null;
      } else if (trimmed.startsWith('AUTHOR:')) {
        const author = trimmed.substring(7).trim();
        if (author.toLowerCase() !== 'unknown') {
          result.author = author;
        }
        currentField = null;
      } else if (trimmed.startsWith('CONTENT:')) {
        result.content = trimmed.substring(8).trim();
        currentField = 'content';
      } else if (currentField === 'content' && trimmed) {
        result.content += '\n\n' + trimmed;
      }
    }

    result.content = result.content.trim();
    return result;
  }

  /**
   * Strip HTML tags from string.
   */
  private stripHtml(html: string): string {
    return html
      .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
      .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
      .replace(/<[^>]+>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  /**
   * Decode HTML entities.
   */
  private decodeHtmlEntities(text: string): string {
    const entities: Record<string, string> = {
      '&amp;': '&',
      '&lt;': '<',
      '&gt;': '>',
      '&quot;': '"',
      '&#39;': "'",
      '&apos;': "'",
      '&nbsp;': ' ',
      '&ndash;': '-',
      '&mdash;': '--',
      '&ldquo;': '"',
      '&rdquo;': '"',
      '&lsquo;': "'",
      '&rsquo;': "'",
    };

    let result = text;
    for (const [entity, char] of Object.entries(entities)) {
      result = result.replace(new RegExp(entity, 'g'), char);
    }

    // Handle numeric entities
    result = result.replace(/&#(\d+);/g, (_, code) => String.fromCharCode(parseInt(code, 10)));

    return result;
  }

  /**
   * Clean extracted content.
   */
  private cleanContent(content: string): string {
    // Strip HTML
    let cleaned = this.stripHtml(content);

    // Decode entities
    cleaned = this.decodeHtmlEntities(cleaned);

    // Normalize whitespace
    cleaned = cleaned
      .replace(/\r\n/g, '\n')
      .replace(/\n{3,}/g, '\n\n')
      .replace(/[ \t]+/g, ' ')
      .trim();

    return cleaned;
  }

  /**
   * Count words in text.
   */
  private countWords(text: string): number {
    return text.split(/\s+/).filter((word) => word.length > 0).length;
  }

  /**
   * Assess extraction quality (0-1).
   */
  private assessQuality(extracted: ExtractedContent, content: string): number {
    let quality = 0.5; // Base quality

    // Bonus for having title
    if (extracted.title && extracted.title.length > 10) {
      quality += 0.1;
    }

    // Bonus for having author
    if (extracted.author) {
      quality += 0.1;
    }

    // Bonus for having date
    if (extracted.publishedDate) {
      quality += 0.05;
    }

    // Bonus for content length
    if (content.length > 500) quality += 0.1;
    if (content.length > 1000) quality += 0.1;
    if (content.length > 2000) quality += 0.05;

    return Math.min(1.0, quality);
  }

  /**
   * Generate article ID from URL.
   */
  private generateArticleId(url: string): string {
    // Simple hash function for article ID
    let hash = 0;
    for (let i = 0; i < url.length; i++) {
      const char = url.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash).toString(16).padStart(16, '0').substring(0, 16);
  }

  /**
   * Get parser statistics.
   */
  getStats(): ParserStats & { successRate: number } {
    const successRate =
      this.stats.parseCount > 0 ? this.stats.successCount / this.stats.parseCount : 0;
    return {
      ...this.stats,
      successRate,
    };
  }

  /**
   * Reset statistics.
   */
  resetStats(): void {
    this.stats = {
      parseCount: 0,
      successCount: 0,
      failureCount: 0,
      totalTimeMs: 0,
    };
  }
}

// ============================================================================
// Internal Types
// ============================================================================

interface ExtractedContent {
  title: string;
  content: string;
  author?: string;
  publishedDate?: string;
}
