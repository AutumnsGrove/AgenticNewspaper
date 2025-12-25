/**
 * Test API Routes (Development only).
 *
 * Simple endpoints for testing without authentication.
 */

import { Hono } from 'hono';
import type { Env, UserPreferences } from '../types';
import { createUser } from '../services/database';
import { SearchService } from '../services/search';
import { LLMService } from '../services/llm';
import { ParserService } from '../services/parser';
import { DigestGenerator } from '../services/digest-generator';

const test = new Hono<{ Bindings: Env }>();

/**
 * POST /test/create-user - Create a test user quickly.
 */
test.post('/create-user', async (c) => {
  const email = `test-${Date.now()}@example.com`;
  const id = crypto.randomUUID();

  try {
    const user = await createUser(c.env.DB, {
      id,
      email,
      subscriptionTier: 'free',
      preferences: {
        topics: [
          {
            name: 'AI & Machine Learning',
            keywords: ['AI', 'machine learning', 'LLM'],
            priority: 5,
            enabled: true,
          },
        ],
        sources: [],
        delivery: {
          frequency: 'daily_am',
          deliveryTimeUtc: '06:00',
          channels: ['web'],
          lookbackHours: 24,
          timezone: 'America/New_York',
        },
        style: {
          tone: 'hn-style',
          skepticismLevel: 4,
          technicalDepth: 4,
          includeBiasAnalysis: false,
          includeCrossConnections: false,
          maxArticlesPerTopic: 5,
        },
        thresholds: {
          minRelevanceScore: 0.5,
          minQualityScore: 0.5,
          minNoveltyScore: 0.3,
          maxBiasScore: 0.8,
        },
      },
    });

    return c.json({
      success: true,
      data: {
        userId: user.id,
        email: user.email,
        message: 'Test user created successfully',
      },
    });
  } catch (error) {
    console.error('Create test user error:', error);
    return c.json(
      {
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to create test user' },
      },
      500
    );
  }
});

/**
 * GET /test/db - Test database connection.
 */
test.get('/db', async (c) => {
  try {
    const result = await c.env.DB.prepare('SELECT 1 as test').first();
    return c.json({
      success: true,
      data: { database: 'connected', result },
    });
  } catch (error) {
    return c.json(
      {
        success: false,
        error: { code: 'DB_ERROR', message: String(error) },
      },
      500
    );
  }
});

/**
 * GET /test/env - Check environment configuration.
 */
test.get('/env', async (c) => {
  return c.json({
    success: true,
    data: {
      environment: c.env.ENVIRONMENT,
      hasOrchestratorUrl: !!c.env.ORCHESTRATOR_API_URL,
      hasOrchestratorKey: !!c.env.ORCHESTRATOR_API_KEY,
      hasOpenRouter: !!c.env.OPENROUTER_API_KEY,
      hasAnthropic: !!c.env.ANTHROPIC_API_KEY,
      hasTavily: !!c.env.TAVILY_API_KEY,
    },
  });
});

// ============================================================================
// New Standalone Service Tests
// ============================================================================

/**
 * GET /test/search - Test Tavily search service.
 */
test.get('/search', async (c) => {
  const query = c.req.query('q') || 'latest AI research news';
  const maxResults = parseInt(c.req.query('max') || '5', 10);

  try {
    const search = SearchService.fromEnv(c.env);
    const results = await search.search(query, { maxResults });

    return c.json({
      success: true,
      data: {
        query,
        resultCount: results.length,
        results: results.map((r) => ({
          title: r.title,
          source: r.source,
          url: r.url,
          relevanceScore: r.relevanceScore,
        })),
        stats: search.getStats(),
      },
    });
  } catch (error) {
    console.error('Search test error:', error);
    return c.json(
      {
        success: false,
        error: {
          code: 'SEARCH_ERROR',
          message: error instanceof Error ? error.message : 'Search failed',
        },
      },
      500
    );
  }
});

/**
 * GET /test/llm - Test OpenRouter LLM service.
 */
test.get('/llm', async (c) => {
  const prompt = c.req.query('prompt') || 'Say "Hello from DeepSeek!" in exactly 5 words.';

  try {
    const llm = LLMService.fromEnv(c.env);
    const response = await llm.complete(prompt, {
      maxTokens: 50,
      temperature: 0.7,
    });

    return c.json({
      success: true,
      data: {
        prompt,
        response: response.content,
        model: response.model,
        tokens: {
          input: response.inputTokens,
          output: response.outputTokens,
          total: response.totalTokens,
        },
        costUsd: response.costUsd,
        responseTimeMs: response.responseTimeMs,
        stats: llm.getStats(),
      },
    });
  } catch (error) {
    console.error('LLM test error:', error);
    return c.json(
      {
        success: false,
        error: {
          code: 'LLM_ERROR',
          message: error instanceof Error ? error.message : 'LLM request failed',
        },
      },
      500
    );
  }
});

/**
 * GET /test/parse - Test article parser.
 */
test.get('/parse', async (c) => {
  const url = c.req.query('url') || 'https://news.ycombinator.com/news';

  try {
    const parser = ParserService.fromEnv(c.env);
    const article = await parser.parseArticle(url, 'Test Article', 'test', {
      useLLM: false,
    });

    if (!article) {
      return c.json({
        success: false,
        error: { code: 'PARSE_FAILED', message: 'Failed to parse article' },
      });
    }

    return c.json({
      success: true,
      data: {
        articleId: article.articleId,
        title: article.title,
        author: article.author,
        source: article.source,
        wordCount: article.wordCount,
        readingTimeMinutes: article.readingTimeMinutes,
        parseQuality: article.parseQuality,
        contentPreview: article.contentPreview,
        stats: parser.getStats(),
      },
    });
  } catch (error) {
    console.error('Parse test error:', error);
    return c.json(
      {
        success: false,
        error: {
          code: 'PARSE_ERROR',
          message: error instanceof Error ? error.message : 'Parse failed',
        },
      },
      500
    );
  }
});

/**
 * POST /test/generate-digest - Test full digest generation (standalone, no Python).
 */
test.post('/generate-digest', async (c) => {
  try {
    // Default test preferences
    const preferences: UserPreferences = {
      topics: [
        {
          name: 'AI & Machine Learning',
          keywords: ['AI', 'machine learning', 'LLM', 'neural network'],
          priority: 5,
          enabled: true,
        },
      ],
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
        skepticismLevel: 4,
        technicalDepth: 4,
        includeBiasAnalysis: false,
        includeCrossConnections: false,
        maxArticlesPerTopic: 3,
      },
      thresholds: {
        minRelevanceScore: 0.5,
        minQualityScore: 0.5,
        minNoveltyScore: 0.3,
        maxBiasScore: 0.8,
      },
    };

    const generator = DigestGenerator.fromEnv(c.env);
    const result = await generator.generateDigest(preferences, {
      maxArticlesPerTopic: 3,
      maxConcurrentParsers: 3,
      lookbackDays: 7,
      useLLMForParsing: false,
    });

    if (!result.success) {
      return c.json(
        {
          success: false,
          error: { code: 'GENERATION_FAILED', message: result.error },
          stats: result.stats,
        },
        500
      );
    }

    return c.json({
      success: true,
      data: {
        digestId: result.digest?.metadata.digestId,
        topicsCovered: result.digest?.metadata.topicsCovered,
        articlesIncluded: result.digest?.metadata.totalArticlesIncluded,
        tokensUsed: result.digest?.metadata.totalTokensUsed,
        costUsd: result.digest?.metadata.totalCostUsd,
        processingTimeSeconds: result.digest?.metadata.processingTimeSeconds,
        markdownLength: result.markdown?.length,
        markdownPreview: result.markdown?.substring(0, 500) + '...',
      },
      stats: result.stats,
    });
  } catch (error) {
    console.error('Generate digest test error:', error);
    return c.json(
      {
        success: false,
        error: {
          code: 'GENERATION_ERROR',
          message: error instanceof Error ? error.message : 'Generation failed',
        },
      },
      500
    );
  }
});

export default test;
