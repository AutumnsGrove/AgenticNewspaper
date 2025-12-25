/**
 * API client for The Daily Clearing Cloudflare Worker
 */

const API_BASE = import.meta.env.VITE_API_URL || 'https://daily-clearing.m7jv4v7npb.workers.dev';

// TODO: Once custom domain is set up, use: https://api.clearing.autumnsgrove.com

interface ApiResponse<T> {
	success: boolean;
	data?: T;
	error?: {
		code: string;
		message: string;
	};
}

/**
 * Generate digest using Cloudflare Durable Objects (fast, serverless)
 */
export async function generateDigestCloudflare(token: string, options?: {
	topics?: string[];
	lookbackHours?: number;
	maxArticles?: number;
}) {
	const response = await fetch(`${API_BASE}/api/digests/generate`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify(options || {}),
	});

	return response.json() as Promise<
		ApiResponse<{
			jobId: string;
			status: string;
			message: string;
		}>
	>;
}

/**
 * Get generation status for Cloudflare mode
 */
export async function getGenerationStatus(token: string) {
	const response = await fetch(`${API_BASE}/api/digests/generate/status`, {
		headers: {
			Authorization: `Bearer ${token}`,
		},
	});

	return response.json() as Promise<
		ApiResponse<{
			status: string;
			progress: number;
			currentStep: string;
			articlesFound: number;
			articlesAnalyzed: number;
		}>
	>;
}

/**
 * Generate digest using Hetzner ephemeral server (advanced processing)
 */
export async function generateDigestServer(userId: string, test = false) {
	const response = await fetch(`${API_BASE}/api/jobs/generate`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({ userId, test }),
	});

	return response.json() as Promise<
		ApiResponse<{
			jobId: string;
			serverId: string;
			serverIp: string;
			status: string;
		}>
	>;
}

/**
 * Get job status
 */
export async function getJobStatus(jobId: string, token: string) {
	const response = await fetch(`${API_BASE}/api/jobs/${jobId}`, {
		headers: {
			Authorization: `Bearer ${token}`,
		},
	});

	return response.json() as Promise<
		ApiResponse<{
			job: any;
			server: any;
			logs: any[];
		}>
	>;
}

/**
 * Get user digests
 */
export async function getUserDigests(token: string) {
	const response = await fetch(`${API_BASE}/api/digests`, {
		headers: {
			Authorization: `Bearer ${token}`,
		},
	});

	return response.json();
}

/**
 * Get a specific digest
 */
export async function getDigest(digestId: string, token: string) {
	const response = await fetch(`${API_BASE}/api/digests/${digestId}`, {
		headers: {
			Authorization: `Bearer ${token}`,
		},
	});

	return response.json();
}

/**
 * Update user preferences
 */
export async function updatePreferences(preferences: any, token: string) {
	const response = await fetch(`${API_BASE}/api/users/me/preferences`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify(preferences),
	});

	return response.json();
}

/**
 * Test endpoint - generate digest without auth
 */
export async function generateTestDigest() {
	const response = await fetch(`${API_BASE}/api/test/provision-job`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
	});

	return response.json() as Promise<
		ApiResponse<{
			jobId: string;
			serverId: string;
			serverIp: string;
			status: string;
			message: string;
		}>
	>;
}
