/**
 * GroveAuth Integration
 * Centralized auth for AutumnsGrove properties
 */

const AUTH_BASE_URL = 'https://auth-api.grove.place';

// ==================== Types ====================

export interface AuthTokens {
	access_token: string;
	refresh_token: string;
	expires_in: number;
	token_type: 'Bearer';
}

export interface AuthUser {
	sub: string;
	email: string;
	name: string | null;
	picture: string | null;
	provider: 'google' | 'github' | 'magic_code';
}

export interface TokenInfo {
	active: boolean;
	sub?: string;
	email?: string;
	name?: string;
	exp?: number;
	client_id?: string;
}

// ==================== PKCE Helpers ====================

export function generateCodeVerifier(): string {
	const array = new Uint8Array(32);
	crypto.getRandomValues(array);
	return base64UrlEncode(array);
}

export async function generateCodeChallenge(verifier: string): Promise<string> {
	const encoder = new TextEncoder();
	const data = encoder.encode(verifier);
	const hash = await crypto.subtle.digest('SHA-256', data);
	return base64UrlEncode(new Uint8Array(hash));
}

function base64UrlEncode(buffer: Uint8Array): string {
	let binary = '';
	for (let i = 0; i < buffer.length; i++) {
		binary += String.fromCharCode(buffer[i]);
	}
	return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

// ==================== Auth Functions ====================

export function getLoginUrl(config: {
	clientId: string;
	redirectUri: string;
	state: string;
	codeChallenge: string;
}): string {
	const params = new URLSearchParams({
		client_id: config.clientId,
		redirect_uri: config.redirectUri,
		state: config.state,
		code_challenge: config.codeChallenge,
		code_challenge_method: 'S256'
	});
	return `https://heartwood.grove.place/login?${params}`;
}

export async function exchangeCode(config: {
	code: string;
	codeVerifier: string;
	clientId: string;
	clientSecret: string;
	redirectUri: string;
}): Promise<AuthTokens> {
	const response = await fetch(`${AUTH_BASE_URL}/token`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
		body: new URLSearchParams({
			grant_type: 'authorization_code',
			code: config.code,
			redirect_uri: config.redirectUri,
			client_id: config.clientId,
			client_secret: config.clientSecret,
			code_verifier: config.codeVerifier
		})
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.error_description || 'Token exchange failed');
	}

	return response.json();
}

export async function verifyToken(accessToken: string): Promise<TokenInfo> {
	const response = await fetch(`${AUTH_BASE_URL}/verify`, {
		headers: { Authorization: `Bearer ${accessToken}` }
	});
	return response.json();
}

export async function getUserInfo(accessToken: string): Promise<AuthUser | null> {
	const response = await fetch(`${AUTH_BASE_URL}/userinfo`, {
		headers: { Authorization: `Bearer ${accessToken}` }
	});

	if (!response.ok) return null;
	return response.json();
}

export async function refreshTokens(config: {
	refreshToken: string;
	clientId: string;
	clientSecret: string;
}): Promise<AuthTokens | null> {
	const response = await fetch(`${AUTH_BASE_URL}/token/refresh`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
		body: new URLSearchParams({
			grant_type: 'refresh_token',
			refresh_token: config.refreshToken,
			client_id: config.clientId,
			client_secret: config.clientSecret
		})
	});

	if (!response.ok) return null;
	return response.json();
}

export async function logout(accessToken: string): Promise<void> {
	await fetch(`${AUTH_BASE_URL}/logout`, {
		method: 'POST',
		headers: { Authorization: `Bearer ${accessToken}` }
	});
}
