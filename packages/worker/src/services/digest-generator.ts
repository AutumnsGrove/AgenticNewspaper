/**
 * Digest Generator - Main orchestration for generating HN-style digests.
 *
 * Ported from Python: packages/core/src/orchestrator/main_orchestrator.py
 * Coordinates search, parsing, and synthesis to create daily digests.
 */

import type { Env, UserPreferences, Digest, DigestMetadata, DigestSection, Article } from '../types';
import { SearchService, type SearchResult } from './search';
import { LLMService } from './llm';
import { ParserService, type ParsedArticle } from './parser';

// ============================================================================
// Constants
// ============================================================================

/** Default maximum articles to fetch per topic */
const DEFAULT_MAX_ARTICLES_PER_TOPIC = 5;

/** Default maximum concurrent article parsers */
const DEFAULT_MAX_CONCURRENT_PARSERS = 5;

/** Default lookback period in days for article search */
const DEFAULT_LOOKBACK_DAYS = 7;

/** Default maximum tokens for search query generation */
const SEARCH_QUERY_MAX_TOKENS = 100;

/** Temperature for search query generation (lower = more deterministic) */
const SEARCH_QUERY_TEMPERATURE = 0.3;

/** Maximum tokens for topic synthesis */
const SYNTHESIS_MAX_TOKENS = 1500;

/** Temperature for synthesis (higher = more creative) */
const SYNTHESIS_TEMPERATURE = 0.7;

/** Maximum content preview length for article synthesis */
const CONTENT_PREVIEW_LENGTH = 800;

// ============================================================================
// Types
// ============================================================================

export interface DigestGeneratorOptions {
  maxArticlesPerTopic?: number;
  maxConcurrentParsers?: number;
  lookbackDays?: number;
  useLLMForParsing?: boolean;
}

export interface GenerationProgress {
  status: string;
  progress: number;
  currentStep: string;
  articlesFound: number;
  articlesParsed: number;
  articlesIncluded: number;
}

export interface GenerationResult {
  success: boolean;
  digest?: Digest;
  markdown?: string;
  error?: string;
  stats: GenerationStats;
}

export interface GenerationStats {
  totalArticlesFound: number;
  totalArticlesParsed: number;
  totalArticlesIncluded: number;
  totalTokensUsed: number;
  totalCostUsd: number;
  processingTimeMs: number;
}

// ============================================================================
// Prompts (from shared/prompts.json)
// ============================================================================

const PROMPTS = {
  searchQueryGeneration: `Generate a search query for finding recent, high-quality articles about: {{topic_name}}

Include these concepts: {{keywords}}
Exclude: {{exclude_keywords}}

Requirements:
- Focus on recent news/research (last 30 days preferred)
- Prefer technical depth over clickbait
- Target sources like HN, ArsTechnica, ArXiv, Nature

Return ONLY the search query, no explanation.`,

  topicSynthesis: `You are writing a Hacker News-style digest section about: {{topic_name}}

Articles to synthesize:
{{articles_text}}

Write an engaging section that:
1. Groups related articles together
2. Uses technical, skeptical HN-style commentary
3. Focuses on "why this matters" and implications
4. Highlights key technical details and trade-offs
5. Avoids hype - be measured and analytical
6. Each article gets 2-3 sentences maximum

Format:
## {{topic_name}}

[Your synthesis of the articles in HN comment style]

### Article Title 1
*Source: [source] | [reading time]*

[2-3 sentence HN-style summary focusing on implications and technical details]

[Source link]

---

Continue for each article. Be concise but insightful.`,

  synthesisSystemPrompt:
    'You are a veteran Hacker News commenter known for technical depth and skeptical analysis.',
};

// ============================================================================
// Digest Generator
// ============================================================================

export class DigestGenerator {
  private search: SearchService;
  private llm: LLMService;
  private parser: ParserService;

  private progress: GenerationProgress = {
    status: 'pending',
    progress: 0,
    currentStep: 'Initializing',
    articlesFound: 0,
    articlesParsed: 0,
    articlesIncluded: 0,
  };

  constructor(search: SearchService, llm: LLMService, parser: ParserService) {
    this.search = search;
    this.llm = llm;
    this.parser = parser;
  }

  /**
   * Create DigestGenerator from environment.
   */
  static fromEnv(env: Env): DigestGenerator {
    const search = SearchService.fromEnv(env);
    const llm = LLMService.fromEnv(env);
    const parser = ParserService.fromEnv(env);
    return new DigestGenerator(search, llm, parser);
  }

  /**
   * Generate a complete digest.
   */
  async generateDigest(
    preferences: UserPreferences,
    options: DigestGeneratorOptions = {}
  ): Promise<GenerationResult> {
    const {
      maxArticlesPerTopic = DEFAULT_MAX_ARTICLES_PER_TOPIC,
      maxConcurrentParsers = DEFAULT_MAX_CONCURRENT_PARSERS,
      lookbackDays = DEFAULT_LOOKBACK_DAYS,
      useLLMForParsing = false,
    } = options;

    const startTime = Date.now();
    const stats: GenerationStats = {
      totalArticlesFound: 0,
      totalArticlesParsed: 0,
      totalArticlesIncluded: 0,
      totalTokensUsed: 0,
      totalCostUsd: 0,
      processingTimeMs: 0,
    };

    try {
      // Step 1: Search for articles
      this.updateProgress('searching', 10, 'Searching for articles');
      const articlesByTopic = await this.searchAllTopics(
        preferences,
        maxArticlesPerTopic,
        lookbackDays
      );
      stats.totalArticlesFound = Object.values(articlesByTopic).flat().length;

      // Step 2: Parse articles
      this.updateProgress('parsing', 30, 'Fetching and parsing articles');
      const parsedByTopic = await this.parseAllArticles(
        articlesByTopic,
        maxConcurrentParsers,
        useLLMForParsing
      );
      stats.totalArticlesParsed = Object.values(parsedByTopic)
        .flat()
        .filter(Boolean).length;

      // Step 3: Synthesize digest
      this.updateProgress('synthesizing', 60, 'Creating HN-style digest');
      const sections = await this.synthesizeDigest(parsedByTopic, preferences);
      stats.totalArticlesIncluded = sections.reduce((sum, s) => sum + s.articles.length, 0);

      // Step 4: Build final digest
      this.updateProgress('complete', 100, 'Digest complete');

      const digestId = new Date().toISOString().split('T')[0];
      const now = new Date().toISOString();

      const metadata: DigestMetadata = {
        digestId,
        generatedAt: now,
        topicsCovered: sections.map((s) => s.topic),
        totalArticlesFound: stats.totalArticlesFound,
        totalArticlesParsed: stats.totalArticlesParsed,
        totalArticlesIncluded: stats.totalArticlesIncluded,
        totalTokensUsed: this.llm.getStats().totalInputTokens + this.llm.getStats().totalOutputTokens,
        totalCostUsd: this.llm.getStats().totalCostUsd,
        processingTimeSeconds: (Date.now() - startTime) / 1000,
      };

      stats.totalTokensUsed = metadata.totalTokensUsed;
      stats.totalCostUsd = metadata.totalCostUsd;
      stats.processingTimeMs = Date.now() - startTime;

      const digest: Digest = {
        metadata,
        sections,
      };

      // Generate markdown
      const markdown = this.generateMarkdown(digest, preferences);

      return {
        success: true,
        digest,
        markdown,
        stats,
      };
    } catch (error) {
      this.updateProgress('failed', 0, `Error: ${error instanceof Error ? error.message : 'Unknown'}`);
      stats.processingTimeMs = Date.now() - startTime;

      return {
        success: false,
        error: error instanceof Error ? error.message : 'Digest generation failed',
        stats,
      };
    }
  }

  /**
   * Search for articles across all configured topics.
   */
  private async searchAllTopics(
    preferences: UserPreferences,
    maxArticlesPerTopic: number,
    lookbackDays: number
  ): Promise<Record<string, SearchResult[]>> {
    const articlesByTopic: Record<string, SearchResult[]> = {};

    for (const topic of preferences.topics) {
      if (!topic.enabled) continue;

      console.log(`Searching: ${topic.name}`);

      // NOTE: LLM-optimized search query generation is available via generateSearchQuery()
      // but currently unused. When direct search support is added, uncomment:
      // const query = await this.generateSearchQuery(topic.name, topic.keywords);

      // Execute search using topic-based search
      const results = await this.search.searchTopic(topic.name, topic.keywords, {
        maxResults: maxArticlesPerTopic * 2, // Get extra for filtering
        daysBack: lookbackDays,
        preferPremiumSources: true,
      });

      articlesByTopic[topic.name] = results.slice(0, maxArticlesPerTopic);
      this.progress.articlesFound += results.length;

      console.log(`  Found: ${results.length} articles`);
    }

    return articlesByTopic;
  }

  /**
   * Generate optimized search query using LLM.
   */
  private async generateSearchQuery(topicName: string, keywords: string[]): Promise<string> {
    const prompt = PROMPTS.searchQueryGeneration
      .replace('{{topic_name}}', topicName)
      .replace('{{keywords}}', keywords.slice(0, 5).join(', '))
      .replace('{{exclude_keywords}}', 'none');

    try {
      const response = await this.llm.complete(prompt, {
        maxTokens: SEARCH_QUERY_MAX_TOKENS,
        temperature: SEARCH_QUERY_TEMPERATURE,
      });
      return response.content.trim().replace(/^["']|["']$/g, '');
    } catch (error) {
      // Log error before falling back to simple query
      console.warn(
        `Search query generation failed for topic "${topicName}":`,
        error instanceof Error ? error.message : error
      );
      return `${topicName} ${keywords.slice(0, 3).join(' ')} latest news`;
    }
  }

  /**
   * Parse all discovered articles.
   */
  private async parseAllArticles(
    articlesByTopic: Record<string, SearchResult[]>,
    maxConcurrent: number,
    useLLM: boolean
  ): Promise<Record<string, ParsedArticle[]>> {
    const parsedByTopic: Record<string, ParsedArticle[]> = {};

    for (const [topicName, searchResults] of Object.entries(articlesByTopic)) {
      console.log(`Parsing ${searchResults.length} articles for: ${topicName}`);

      const articlesToParse = searchResults.map((r) => ({
        url: r.url,
        title: r.title,
        source: r.source,
      }));

      const parsed = await this.parser.parseArticles(articlesToParse, {
        maxConcurrent,
        useLLM,
      });

      // Filter out failed parses
      const successful = parsed.filter((p): p is ParsedArticle => p !== null);
      parsedByTopic[topicName] = successful;
      this.progress.articlesParsed += successful.length;

      console.log(`  Successfully parsed: ${successful.length}/${searchResults.length}`);
    }

    return parsedByTopic;
  }

  /**
   * Synthesize HN-style digest from parsed articles.
   */
  private async synthesizeDigest(
    parsedByTopic: Record<string, ParsedArticle[]>,
    _preferences: UserPreferences
  ): Promise<DigestSection[]> {
    const sections: DigestSection[] = [];

    for (const [topicName, articles] of Object.entries(parsedByTopic)) {
      if (articles.length === 0) continue;

      console.log(`Synthesizing section: ${topicName}`);

      // Format articles for synthesis using array-based concatenation for efficiency
      const articleParts: string[] = [];
      for (let i = 0; i < articles.length; i++) {
        const a = articles[i];
        // slice() handles length automatically - no ternary needed
        const contentPreview = a.content.slice(0, CONTENT_PREVIEW_LENGTH);
        articleParts.push(
          `Article ${i + 1}:\nTitle: ${a.title}\nSource: ${a.source}\nURL: ${a.url}\nReading Time: ${a.readingTimeMinutes} min\nContent Preview:\n${contentPreview}`
        );
      }
      const articlesText = articleParts.join('\n---\n');

      // Generate synthesis
      const prompt = PROMPTS.topicSynthesis
        .replace(/\{\{topic_name\}\}/g, topicName)
        .replace('{{articles_text}}', articlesText);

      const response = await this.llm.complete(prompt, {
        maxTokens: SYNTHESIS_MAX_TOKENS,
        temperature: SYNTHESIS_TEMPERATURE,
        systemPrompt: PROMPTS.synthesisSystemPrompt,
      });

      // Convert parsed articles to Article format
      const digestArticles: Article[] = articles.map((a) => ({
        id: a.articleId,
        url: a.url,
        title: a.title,
        source: a.source,
        author: a.author,
        publishedDate: a.publishedDate,
        wordCount: a.wordCount,
        readingTimeMinutes: a.readingTimeMinutes,
        summary: a.contentPreview,
        keyPoints: [],
        technicalInsights: [],
        relevanceScore: 0.7,
        qualityScore: a.parseQuality,
        noveltyScore: 0.5,
        biasScore: 0,
        biasDirection: 'unknown',
        redFlags: [],
        technicalLevel: 3,
      }));

      sections.push({
        topic: topicName,
        sectionSummary: response.content,
        articles: digestArticles,
        crossStoryInsights: [],
      });

      this.progress.articlesIncluded += articles.length;
    }

    return sections;
  }

  /**
   * Generate markdown from digest.
   */
  private generateMarkdown(digest: Digest, _preferences: UserPreferences): string {
    const parts: string[] = [];

    // Header
    const date = new Date().toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
    parts.push(`# Daily Tech Digest

**${date}**

*Your personalized HN-style news digest*

---`);

    // Sections (from synthesis)
    for (const section of digest.sections) {
      parts.push(section.sectionSummary);
    }

    // Footer
    parts.push(`---

## Digest Stats

- **Articles Found**: ${digest.metadata.totalArticlesFound}
- **Articles Parsed**: ${digest.metadata.totalArticlesParsed}
- **Articles Included**: ${digest.metadata.totalArticlesIncluded}
- **Topics**: ${digest.metadata.topicsCovered.join(', ')}
- **Processing Time**: ${digest.metadata.processingTimeSeconds.toFixed(1)}s
- **Total Tokens Used**: ${digest.metadata.totalTokensUsed.toLocaleString()}
- **Estimated Cost**: $${digest.metadata.totalCostUsd.toFixed(4)}

---

*Generated by The Daily Clearing v1.0*
*${new Date().toISOString()}*`);

    return parts.join('\n\n');
  }

  /**
   * Update progress state.
   */
  private updateProgress(status: string, progress: number, currentStep: string): void {
    this.progress = {
      ...this.progress,
      status,
      progress,
      currentStep,
    };
  }

  /**
   * Get current progress.
   */
  getProgress(): GenerationProgress {
    return { ...this.progress };
  }

  /**
   * Reset generator state.
   */
  reset(): void {
    this.progress = {
      status: 'pending',
      progress: 0,
      currentStep: 'Initializing',
      articlesFound: 0,
      articlesParsed: 0,
      articlesIncluded: 0,
    };
    this.search.resetStats();
    this.llm.resetStats();
    this.parser.resetStats();
  }
}
