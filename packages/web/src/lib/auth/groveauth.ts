/**
 * Heartwood Session-Based Authentication
 *
 * Uses SessionDO (Durable Object sessions) instead of OAuth tokens.
 * Session cookie: grove_session={sessionId}:{userId}:{signature}
 * Domain: .grove.place (works across all subdomains)
 */

const AUTH_API_URL = 'https://auth-api.grove.place';
const AUTH_FRONTEND_URL = 'https://heartwood.grove.place';

// ==================== Types ====================

export interface SessionUser {
	id: string;
	email: string;
	name: string | null;
	avatarUrl: string | null;
	isAdmin: boolean;
}

export interface Session {
	id: string;
	deviceName: string | null;
	lastActiveAt: string;
}

export interface SessionValidationResponse {
	valid: boolean;
	user: SessionUser | null;
	session: Session | null;
}

// ==================== Session Validation ====================

/**
 * Validate the current session by forwarding cookies to Heartwood
 */
export async function validateSession(cookieHeader: string): Promise<SessionValidationResponse> {
	const response = await fetch(`${AUTH_API_URL}/session/validate`, {
		method: 'POST',
		headers: {
			Cookie: cookieHeader,
		},
	});

	if (!response.ok) {
		return { valid: false, user: null, session: null };
	}

	return response.json();
}

// ==================== Login URL ====================

/**
 * Get the login URL to redirect users to Heartwood
 */
export function getLoginUrl(config: {
	clientId: string;
	redirectUri: string;
}): string {
	const params = new URLSearchParams({
		client_id: config.clientId,
		redirect_uri: config.redirectUri,
	});
	return `${AUTH_FRONTEND_URL}/login?${params}`;
}

// ==================== Logout ====================

/**
 * Revoke the current session (logout from this device)
 */
export async function revokeSession(cookieHeader: string): Promise<boolean> {
	const response = await fetch(`${AUTH_API_URL}/session/revoke`, {
		method: 'POST',
		headers: {
			Cookie: cookieHeader,
		},
	});
	return response.ok;
}

/**
 * Revoke all sessions (logout from all devices)
 */
export async function revokeAllSessions(cookieHeader: string): Promise<boolean> {
	const response = await fetch(`${AUTH_API_URL}/session/revoke-all`, {
		method: 'POST',
		headers: {
			Cookie: cookieHeader,
		},
	});
	return response.ok;
}

// ==================== Session Management ====================

/**
 * List all active sessions for the current user
 */
export async function listSessions(cookieHeader: string): Promise<Session[]> {
	const response = await fetch(`${AUTH_API_URL}/session/list`, {
		headers: {
			Cookie: cookieHeader,
		},
	});

	if (!response.ok) {
		return [];
	}

	const data = await response.json();
	return data.sessions || [];
}

/**
 * Revoke a specific session by ID
 */
export async function revokeSessionById(
	sessionId: string,
	cookieHeader: string
): Promise<boolean> {
	const response = await fetch(`${AUTH_API_URL}/session/${sessionId}`, {
		method: 'DELETE',
		headers: {
			Cookie: cookieHeader,
		},
	});
	return response.ok;
}
