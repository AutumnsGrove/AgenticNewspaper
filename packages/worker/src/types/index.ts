/**
 * Type definitions for The Daily Clearing Worker.
 * These types mirror the Python models in packages/core.
 */

// ============================================================================
// Environment Bindings
// ============================================================================

export interface Env {
  // D1 Database
  DB: D1Database;

  // R2 Storage
  DIGESTS: R2Bucket;
  CACHE: R2Bucket;
  R2_BUCKET: R2Bucket;

  // Durable Objects
  DIGEST_JOB: DurableObjectNamespace;
  USER_STATE: DurableObjectNamespace;

  // KV Namespaces
  RATE_LIMIT: KVNamespace;
  SESSIONS: KVNamespace;

  // Environment variables
  ENVIRONMENT: string;
  WORKER_URL?: string;
  WEB_URL?: string;

  // Orchestrator API (Python core service)
  ORCHESTRATOR_API_URL?: string;
  ORCHESTRATOR_API_KEY?: string;

  // GroveAuth / Heartwood
  HEARTWOOD_CLIENT_ID?: string;
  HEARTWOOD_CLIENT_SECRET?: string;

  // Webhook verification
  WEBHOOK_SECRET?: string;

  // Secrets (set via wrangler secret)
  OPENROUTER_API_KEY?: string;
  ANTHROPIC_API_KEY?: string;
  TAVILY_API_KEY?: string;
  RESEND_API_KEY?: string;
  JWT_SECRET?: string;
}

// ============================================================================
// User Types
// ============================================================================

export interface User {
  id: string;
  email: string;
  createdAt: string;
  subscriptionTier: 'free' | 'basic' | 'pro';
  preferences: UserPreferences;
  rssToken?: string;
}

export interface UserPreferences {
  topics: Topic[];
  sources: SourceConfig[];
  delivery: DeliveryConfig;
  style: StyleConfig;
  thresholds: ThresholdConfig;
}

export interface Topic {
  name: string;
  keywords: string[];
  priority: number; // 1-5
  enabled: boolean;
}

export interface SourceConfig {
  domain: string;
  trust: number; // 0.0-1.0
  priority: number; // 1-5
}

export interface DeliveryConfig {
  frequency: 'hourly' | 'daily_am' | 'daily_pm' | 'weekly' | 'biweekly' | 'monthly';
  deliveryTimeUtc: string; // "06:00"
  channels: Channel[];
  lookbackHours: number;
  timezone: string;
}

export type Channel = 'web' | 'rss' | 'email';

export interface StyleConfig {
  tone: 'hn-style' | 'formal' | 'casual';
  skepticismLevel: number; // 1-5
  technicalDepth: number; // 1-5
  includeBiasAnalysis: boolean;
  includeCrossConnections: boolean;
  maxArticlesPerTopic: number;
}

export interface ThresholdConfig {
  minRelevanceScore: number;
  minQualityScore: number;
  minNoveltyScore: number;
  maxBiasScore: number;
}

// ============================================================================
// Article Types
// ============================================================================

export interface Article {
  id: string;
  url: string;
  title: string;
  source: string;
  author?: string;
  publishedDate?: string;
  wordCount: number;
  readingTimeMinutes: number;
  summary: string;
  keyPoints: string[];
  whyMatters?: string;
  technicalInsights: string[];
  relevanceScore: number;
  qualityScore: number;
  noveltyScore: number;
  biasScore: number;
  biasDirection: BiasDirection;
  skepticsCorner?: string;
  redFlags: string[];
  technicalLevel: number;
}

export type BiasDirection = 'left' | 'center-left' | 'center' | 'center-right' | 'right' | 'unknown';

export interface ArticleMetadata {
  fetchedAt: string;
  parsedAt: string;
  analyzedAt: string;
  topic: string;
  contentHash: string;
}

// ============================================================================
// Digest Types
// ============================================================================

export interface Digest {
  metadata: DigestMetadata;
  sections: DigestSection[];
  crossStoryConnections?: string;
  skepticsSummary?: string;
}

export interface DigestMetadata {
  digestId: string;
  userId?: string;
  generatedAt: string;
  periodStart?: string;
  periodEnd?: string;
  frequency?: string;
  topicsCovered: string[];
  totalArticlesFound: number;
  totalArticlesParsed: number;
  totalArticlesIncluded: number;
  totalTokensUsed: number;
  totalCostUsd: number;
  processingTimeSeconds: number;
}

export interface DigestSection {
  topic: string;
  sectionSummary: string;
  articles: Article[];
  crossStoryInsights: string[];
}

// ============================================================================
// Digest Job Types
// ============================================================================

export type JobStatus =
  | 'pending'
  | 'searching'
  | 'fetching'
  | 'parsing'
  | 'analyzing'
  | 'synthesizing'
  | 'complete'
  | 'failed';

export interface DigestJobState {
  id: string;
  userId: string;
  status: JobStatus;
  batchNum: number;
  articlesFound: number;
  articlesParsed: number;
  articlesAnalyzed: number;
  currentTopic?: string;
  errorMessage?: string;
  startedAt: string;
  updatedAt: string;
  completedAt?: string;
  digestId?: string;
}

export interface DigestJobProgress {
  status: JobStatus;
  progress: number; // 0-100
  currentStep: string;
  articlesFound: number;
  articlesAnalyzed: number;
  estimatedTimeRemaining?: number;
}

// ============================================================================
// API Types
// ============================================================================

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
  meta?: ResponseMeta;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ResponseMeta {
  requestId: string;
  timestamp: string;
  processingTimeMs: number;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

// ============================================================================
// Authentication Types
// ============================================================================

export interface AuthToken {
  userId: string;
  email: string;
  tier: 'free' | 'basic' | 'pro';
  exp: number;
  iat: number;
}

export interface Session {
  userId: string;
  createdAt: string;
  expiresAt: string;
  userAgent?: string;
  ip?: string;
}

// ============================================================================
// Rate Limiting Types
// ============================================================================

export interface RateLimitConfig {
  windowMs: number;
  maxRequests: number;
}

export interface RateLimitInfo {
  remaining: number;
  reset: number;
  limit: number;
}

// ============================================================================
// Feedback Types
// ============================================================================

export type FeedbackType = 'like' | 'dislike' | 'read' | 'skip' | 'share' | 'save';

export interface Feedback {
  id: string;
  userId: string;
  digestId: string;
  articleUrl?: string;
  type: FeedbackType;
  createdAt: string;
  notes?: string;
}

// ============================================================================
// Usage Tracking Types
// ============================================================================

export interface UsageRecord {
  userId: string;
  month: string; // YYYY-MM
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
  digestCount: number;
  articlesFetched: number;
  articlesAnalyzed: number;
}

export interface UsageLimits {
  tier: 'free' | 'basic' | 'pro';
  maxDigestsPerMonth: number;
  maxArticlesPerDigest: number;
  maxTopics: number;
  maxOnDemand: number;
}

export const USAGE_LIMITS: Record<string, UsageLimits> = {
  free: {
    tier: 'free',
    maxDigestsPerMonth: 4,
    maxArticlesPerDigest: 10,
    maxTopics: 3,
    maxOnDemand: 1,
  },
  basic: {
    tier: 'basic',
    maxDigestsPerMonth: 30,
    maxArticlesPerDigest: 20,
    maxTopics: 10,
    maxOnDemand: 10,
  },
  pro: {
    tier: 'pro',
    maxDigestsPerMonth: -1, // unlimited
    maxArticlesPerDigest: 50,
    maxTopics: -1, // unlimited
    maxOnDemand: -1, // unlimited
  },
};
