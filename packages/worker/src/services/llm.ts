/**
 * LLM Service - OpenRouter/DeepSeek provider for AI completions.
 *
 * Ported from Python: packages/core/src/providers/openrouter.py
 * Primary provider is DeepSeek V3.2 via OpenRouter (~10x cheaper than Claude).
 */

import type { Env } from '../types';

// ============================================================================
// Types
// ============================================================================

export interface LLMResponse {
  content: string;
  model: string;
  provider: string;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  costUsd: number;
  responseTimeMs: number;
  finishReason: string;
}

export interface CompletionOptions {
  maxTokens?: number;
  temperature?: number;
  systemPrompt?: string;
  stopSequences?: string[];
  topP?: number;
}

export interface ModelInfo {
  modelId: string;
  name: string;
  provider: string;
  contextLength: number;
  inputCostPerMillion: number;
  outputCostPerMillion: number;
}

export interface LLMStats {
  totalRequests: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  totalCostUsd: number;
  totalTimeMs: number;
  errors: number;
  rateLimits: number;
}

// ============================================================================
// Constants
// ============================================================================

const OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1';

// Model definitions - costs from OpenRouter
export const MODELS: Record<string, ModelInfo> = {
  'deepseek/deepseek-chat': {
    modelId: 'deepseek/deepseek-chat',
    name: 'DeepSeek V3.2',
    provider: 'deepseek',
    contextLength: 64000,
    inputCostPerMillion: 0.27,
    outputCostPerMillion: 1.1,
  },
  'deepseek/deepseek-r1': {
    modelId: 'deepseek/deepseek-r1',
    name: 'DeepSeek R1',
    provider: 'deepseek',
    contextLength: 64000,
    inputCostPerMillion: 0.55,
    outputCostPerMillion: 2.19,
  },
  'anthropic/claude-3.5-haiku': {
    modelId: 'anthropic/claude-3.5-haiku',
    name: 'Claude 3.5 Haiku',
    provider: 'anthropic',
    contextLength: 200000,
    inputCostPerMillion: 0.8,
    outputCostPerMillion: 4.0,
  },
  'anthropic/claude-sonnet-4': {
    modelId: 'anthropic/claude-sonnet-4',
    name: 'Claude Sonnet 4',
    provider: 'anthropic',
    contextLength: 200000,
    inputCostPerMillion: 3.0,
    outputCostPerMillion: 15.0,
  },
};

export const DEFAULT_MODEL = 'deepseek/deepseek-chat';

// ============================================================================
// LLM Service
// ============================================================================

export class LLMService {
  private apiKey: string;
  private model: string;
  private modelInfo: ModelInfo;
  private siteUrl: string;
  private siteName: string;
  private stats: LLMStats = {
    totalRequests: 0,
    totalInputTokens: 0,
    totalOutputTokens: 0,
    totalCostUsd: 0,
    totalTimeMs: 0,
    errors: 0,
    rateLimits: 0,
  };

  constructor(
    apiKey: string,
    model: string = DEFAULT_MODEL,
    siteUrl: string = 'https://clearing.autumnsgrove.com',
    siteName: string = 'The Daily Clearing'
  ) {
    this.apiKey = apiKey;
    this.model = model;
    this.siteUrl = siteUrl;
    this.siteName = siteName;

    const info = MODELS[model];
    if (!info) {
      throw new Error(`Unknown model: ${model}. Available: ${Object.keys(MODELS).join(', ')}`);
    }
    this.modelInfo = info;
  }

  /**
   * Create LLMService from environment.
   */
  static fromEnv(env: Env, model?: string): LLMService {
    const apiKey = env.OPENROUTER_API_KEY;
    if (!apiKey) {
      throw new Error('OPENROUTER_API_KEY not configured');
    }
    return new LLMService(apiKey, model || DEFAULT_MODEL);
  }

  /**
   * Complete a prompt using OpenRouter.
   */
  async complete(prompt: string, options: CompletionOptions = {}): Promise<LLMResponse> {
    // Input validation
    if (!prompt || typeof prompt !== 'string') {
      throw new LLMError('Prompt must be a non-empty string', 400);
    }
    if (prompt.length === 0) {
      throw new LLMError('Prompt cannot be empty', 400);
    }

    // Estimate token count (~3 chars per token for safety margin)
    // Using conservative estimate to account for non-English text, code, and JSON
    const estimatedTokens = Math.ceil(prompt.length / 3);
    const maxContextTokens = this.modelInfo.contextLength;
    // Reserve 20% of context for response and system prompt overhead
    const maxInputTokens = Math.floor(maxContextTokens * 0.8);
    if (estimatedTokens > maxInputTokens) {
      throw new LLMError(
        `Prompt too long: estimated ${estimatedTokens} tokens exceeds limit of ${maxInputTokens} tokens for model ${this.model}`,
        400
      );
    }

    const { maxTokens = 1024, temperature = 0.7, systemPrompt, stopSequences, topP } = options;

    const startTime = Date.now();

    // Build messages
    const messages: Array<{ role: string; content: string }> = [];
    if (systemPrompt) {
      messages.push({ role: 'system', content: systemPrompt });
    }
    messages.push({ role: 'user', content: prompt });

    // Build payload
    const payload: Record<string, unknown> = {
      model: this.model,
      messages,
      max_tokens: maxTokens,
      temperature,
    };

    if (stopSequences && stopSequences.length > 0) {
      payload.stop = stopSequences;
    }
    if (topP !== undefined) {
      payload.top_p = topP;
    }

    try {
      const response = await fetch(`${OPENROUTER_BASE_URL}/chat/completions`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${this.apiKey}`,
          'HTTP-Referer': this.siteUrl,
          'X-Title': this.siteName,
          'X-Data-Policy': 'deny', // Zero data retention
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        return this.handleError(response);
      }

      const rawData = await response.json();
      const data = validateOpenRouterResponse(rawData);
      const result = this.parseResponse(data, startTime);

      // Update stats
      this.stats.totalRequests++;
      this.stats.totalInputTokens += result.inputTokens;
      this.stats.totalOutputTokens += result.outputTokens;
      this.stats.totalCostUsd += result.costUsd;
      this.stats.totalTimeMs += result.responseTimeMs;

      return result;
    } catch (error) {
      if (error instanceof LLMError) {
        throw error;
      }
      this.stats.errors++;
      throw new LLMError(
        `LLM request failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        0
      );
    }
  }

  /**
   * Parse OpenRouter response.
   */
  private parseResponse(data: OpenRouterResponse, startTime: number): LLMResponse {
    const choice = data.choices?.[0];
    if (!choice) {
      throw new LLMError('Invalid response: no choices returned', 0);
    }

    const content = choice.message?.content || '';
    const finishReason = choice.finish_reason || 'stop';

    const usage = data.usage || { prompt_tokens: 0, completion_tokens: 0 };
    const inputTokens = usage.prompt_tokens;
    const outputTokens = usage.completion_tokens;

    // Calculate cost
    const costUsd = this.calculateCost(inputTokens, outputTokens);
    const responseTimeMs = Date.now() - startTime;

    return {
      content,
      model: this.model,
      provider: 'openrouter',
      inputTokens,
      outputTokens,
      totalTokens: inputTokens + outputTokens,
      costUsd,
      responseTimeMs,
      finishReason,
    };
  }

  /**
   * Calculate cost for tokens.
   */
  calculateCost(inputTokens: number, outputTokens: number): number {
    const inputCost = (inputTokens / 1_000_000) * this.modelInfo.inputCostPerMillion;
    const outputCost = (outputTokens / 1_000_000) * this.modelInfo.outputCostPerMillion;
    return inputCost + outputCost;
  }

  /**
   * Handle HTTP errors from OpenRouter.
   */
  private async handleError(response: Response): Promise<never> {
    let errorMessage: string;
    try {
      const errorData = (await response.json()) as { error?: { message?: string } };
      errorMessage = errorData.error?.message || response.statusText;
    } catch {
      errorMessage = response.statusText;
    }

    this.stats.errors++;

    switch (response.status) {
      case 401:
        throw new AuthenticationError(`Invalid API key: ${errorMessage}`);
      case 429:
        this.stats.rateLimits++;
        const retryAfter = response.headers.get('Retry-After');
        throw new RateLimitError(
          `Rate limit exceeded: ${errorMessage}`,
          retryAfter ? parseFloat(retryAfter) : undefined
        );
      case 404:
        throw new ModelNotFoundError(`Model not found: ${errorMessage}`);
      default:
        throw new LLMError(`Request failed (${response.status}): ${errorMessage}`, response.status);
    }
  }

  /**
   * Get current model info.
   */
  getModelInfo(): ModelInfo {
    return { ...this.modelInfo };
  }

  /**
   * Get service statistics.
   */
  getStats(): LLMStats & { averageCostPerRequest: number; averageTokensPerRequest: number } {
    const avgCost =
      this.stats.totalRequests > 0 ? this.stats.totalCostUsd / this.stats.totalRequests : 0;
    const avgTokens =
      this.stats.totalRequests > 0
        ? (this.stats.totalInputTokens + this.stats.totalOutputTokens) / this.stats.totalRequests
        : 0;

    return {
      ...this.stats,
      averageCostPerRequest: avgCost,
      averageTokensPerRequest: avgTokens,
    };
  }

  /**
   * Reset statistics.
   */
  resetStats(): void {
    this.stats = {
      totalRequests: 0,
      totalInputTokens: 0,
      totalOutputTokens: 0,
      totalCostUsd: 0,
      totalTimeMs: 0,
      errors: 0,
      rateLimits: 0,
    };
  }

  /**
   * Change model (creates new instance).
   */
  withModel(model: string): LLMService {
    return new LLMService(this.apiKey, model, this.siteUrl, this.siteName);
  }
}

// ============================================================================
// OpenRouter API Types
// ============================================================================

interface OpenRouterResponse {
  id: string;
  choices: Array<{
    message: {
      role: string;
      content: string;
    };
    finish_reason: string;
  }>;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens?: number;
  };
  model?: string;
}

/**
 * Runtime validation for OpenRouter API response.
 * Validates critical fields to catch API changes early.
 */
function validateOpenRouterResponse(data: unknown): OpenRouterResponse {
  if (!data || typeof data !== 'object') {
    throw new LLMError('Invalid response: expected object', 0);
  }

  const response = data as Record<string, unknown>;

  if (!Array.isArray(response.choices)) {
    throw new LLMError('Invalid response: missing or invalid choices array', 0);
  }

  if (response.choices.length === 0) {
    throw new LLMError('Invalid response: empty choices array', 0);
  }

  const firstChoice = response.choices[0] as Record<string, unknown>;
  if (!firstChoice || typeof firstChoice !== 'object') {
    throw new LLMError('Invalid response: invalid choice object', 0);
  }

  const message = firstChoice.message as Record<string, unknown>;
  if (!message || typeof message !== 'object') {
    throw new LLMError('Invalid response: missing message in choice', 0);
  }

  if (typeof message.content !== 'string') {
    throw new LLMError('Invalid response: missing or invalid content in message', 0);
  }

  return data as OpenRouterResponse;
}

// ============================================================================
// Error Types
// ============================================================================

export class LLMError extends Error {
  statusCode: number;

  constructor(message: string, statusCode: number) {
    super(message);
    this.name = 'LLMError';
    this.statusCode = statusCode;
  }
}

export class AuthenticationError extends LLMError {
  constructor(message: string) {
    super(message, 401);
    this.name = 'AuthenticationError';
  }
}

export class RateLimitError extends LLMError {
  retryAfter?: number;

  constructor(message: string, retryAfter?: number) {
    super(message, 429);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

export class ModelNotFoundError extends LLMError {
  constructor(message: string) {
    super(message, 404);
    this.name = 'ModelNotFoundError';
  }
}
