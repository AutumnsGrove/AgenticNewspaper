/**
 * API client for The Daily Clearing Cloudflare Worker
 */

const API_BASE = import.meta.env.VITE_API_URL || 'https://daily-clearing.m7jv4v7npb.workers.dev';

interface ApiResponse<T> {
	success: boolean;
	data?: T;
	error?: {
		code: string;
		message: string;
	};
}

/**
 * Generate a new digest
 */
export async function generateDigest(userId: string, test = false) {
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
