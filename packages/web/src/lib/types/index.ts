/**
 * Type definitions for The Daily Clearing web app.
 */

export interface Article {
	id: string;
	url: string;
	title: string;
	source: string;
	author?: string;
	publishedDate?: string;
	wordCount: number;
	readingTimeMinutes: number;

	// Quality analysis
	relevanceScore: number;
	qualityScore: number;
	noveltyScore: number;
	biasScore: number;
	technicalLevel: number;

	// Content
	summary: string;
	keyPoints: string[];
	whyMatters: string;
	technicalInsights: string[];

	// Bias analysis
	biasDirection: 'left' | 'center_left' | 'center' | 'center_right' | 'right' | 'unknown';
	skepticsCorner?: string;
	redFlags: string[];
}

export interface DigestSection {
	topic: string;
	articles: Article[];
	sectionSummary?: string;
	crossStoryInsights: string[];
}

export interface DigestMetadata {
	digestId: string;
	generatedAt: string;
	topicsCovered: string[];
	totalArticlesFound: number;
	totalArticlesParsed: number;
	totalArticlesIncluded: number;
	totalTokensUsed: number;
	totalCostUsd: number;
	processingTimeSeconds: number;
}

export interface Digest {
	metadata: DigestMetadata;
	sections: DigestSection[];
	crossStoryConnections?: string;
	skepticsSummary?: string;
	markdown?: string;
}

export interface User {
	id: string;
	email: string;
	subscriptionTier: 'free' | 'basic' | 'pro';
	createdAt: string;
}

export interface UserPreferences {
	topics: TopicPreference[];
	deliveryFrequency: 'hourly' | 'daily' | 'weekly' | 'biweekly' | 'monthly';
	deliveryTime: string;
	channels: ('web' | 'rss' | 'email')[];
	style: StylePreferences;
}

export interface TopicPreference {
	name: string;
	keywords: string[];
	priority: number;
	enabled: boolean;
}

export interface StylePreferences {
	tone: 'hn-style' | 'formal' | 'casual';
	skepticismLevel: number;
	technicalDepth: number;
	includeBiasAnalysis: boolean;
	includeCrossConnections: boolean;
}

export interface FeedbackData {
	articleUrl?: string;
	digestId: string;
	type: 'like' | 'dislike' | 'read' | 'skip';
	rating?: number;
	comment?: string;
}

export interface ApiError {
	message: string;
	code?: string;
	details?: Record<string, unknown>;
}
