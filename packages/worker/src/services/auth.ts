/**
 * GroveAuth (Heartwood) integration service.
 *
 * Handles OAuth 2.0 authentication flow with PKCE.
 * Heartwood is the centralized auth service for AutumnsGrove properties.
 */

import type { Env } from '../types';

// Heartwood OAuth configuration
const HEARTWOOD_BASE_URL = 'https://heartwood.grove.place';
const CLIENT_ID = 'daily-clearing';

export interface HeartWoodTokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
}

export interface HeartWoodUser {
  id: string;
  email: string;
  name: string | null;
  picture: string | null;
  provider: string;
  created_at: string;
}

/**
 * Generate a random string for PKCE code verifier.
 */
export function generateCodeVerifier(): string {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return base64UrlEncode(array);
}

/**
 * Generate code challenge from verifier using SHA-256.
 */
export async function generateCodeChallenge(verifier: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return base64UrlEncode(new Uint8Array(hash));
}

/**
 * Base64 URL encode bytes.
 */
function base64UrlEncode(bytes: Uint8Array): string {
  const binString = Array.from(bytes, (byte) => String.fromCodePoint(byte)).join('');
  return btoa(binString)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

/**
 * Generate the Heartwood login URL for OAuth flow.
 */
export function getLoginUrl(
  redirectUri: string,
  state: string,
  codeChallenge: string
): string {
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: redirectUri,
    response_type: 'code',
    state,
    code_challenge: codeChallenge,
    code_challenge_method: 'S256',
  });

  return `${HEARTWOOD_BASE_URL}/login?${params.toString()}`;
}

/**
 * Exchange authorization code for tokens.
 */
export async function exchangeCodeForTokens(
  code: string,
  redirectUri: string,
  codeVerifier: string,
  clientSecret: string
): Promise<HeartWoodTokens> {
  const response = await fetch(`${HEARTWOOD_BASE_URL}/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code,
      redirect_uri: redirectUri,
      client_id: CLIENT_ID,
      client_secret: clientSecret,
      code_verifier: codeVerifier,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Token exchange failed: ${error}`);
  }

  return response.json();
}

/**
 * Refresh an access token using a refresh token.
 */
export async function refreshAccessToken(
  refreshToken: string,
  clientSecret: string
): Promise<HeartWoodTokens> {
  const response = await fetch(`${HEARTWOOD_BASE_URL}/token/refresh`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'refresh_token',
      refresh_token: refreshToken,
      client_id: CLIENT_ID,
      client_secret: clientSecret,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Token refresh failed: ${error}`);
  }

  return response.json();
}

/**
 * Verify an access token with Heartwood.
 */
export async function verifyToken(accessToken: string): Promise<HeartWoodUser | null> {
  const response = await fetch(`${HEARTWOOD_BASE_URL}/verify`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    return null;
  }

  return response.json();
}

/**
 * Get user info from Heartwood.
 */
export async function getUserInfo(accessToken: string): Promise<HeartWoodUser | null> {
  const response = await fetch(`${HEARTWOOD_BASE_URL}/userinfo`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    return null;
  }

  return response.json();
}

/**
 * Revoke tokens (logout).
 */
export async function revokeTokens(accessToken: string): Promise<void> {
  await fetch(`${HEARTWOOD_BASE_URL}/logout`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

/**
 * Store PKCE state in KV for callback verification.
 */
export async function storePKCEState(
  env: Env,
  state: string,
  codeVerifier: string,
  redirectUri: string
): Promise<void> {
  await env.SESSIONS.put(
    `pkce:${state}`,
    JSON.stringify({ codeVerifier, redirectUri }),
    { expirationTtl: 600 } // 10 minutes
  );
}

/**
 * Retrieve and delete PKCE state from KV.
 */
export async function getPKCEState(
  env: Env,
  state: string
): Promise<{ codeVerifier: string; redirectUri: string } | null> {
  const data = await env.SESSIONS.get(`pkce:${state}`);
  if (!data) return null;

  // Delete after retrieval (one-time use)
  await env.SESSIONS.delete(`pkce:${state}`);

  return JSON.parse(data);
}

/**
 * Store user session after successful auth.
 */
export async function createSession(
  env: Env,
  userId: string,
  accessToken: string,
  refreshToken: string,
  expiresIn: number
): Promise<string> {
  const sessionId = crypto.randomUUID();

  await env.SESSIONS.put(
    `session:${sessionId}`,
    JSON.stringify({
      userId,
      accessToken,
      refreshToken,
      createdAt: Date.now(),
    }),
    { expirationTtl: expiresIn }
  );

  return sessionId;
}

/**
 * Get session data from KV.
 */
export async function getSession(
  env: Env,
  sessionId: string
): Promise<{
  userId: string;
  accessToken: string;
  refreshToken: string;
  createdAt: number;
} | null> {
  const data = await env.SESSIONS.get(`session:${sessionId}`);
  if (!data) return null;
  return JSON.parse(data);
}

/**
 * Delete session (logout).
 */
export async function deleteSession(env: Env, sessionId: string): Promise<void> {
  await env.SESSIONS.delete(`session:${sessionId}`);
}

/**
 * Middleware to extract and verify session from cookie.
 */
export async function getAuthenticatedUser(
  env: Env,
  request: Request
): Promise<{ userId: string; accessToken: string } | null> {
  // Get session ID from cookie
  const cookie = request.headers.get('Cookie');
  if (!cookie) return null;

  const sessionMatch = cookie.match(/session=([^;]+)/);
  if (!sessionMatch) return null;

  const sessionId = sessionMatch[1];
  const session = await getSession(env, sessionId);
  if (!session) return null;

  // Verify token is still valid with Heartwood
  const user = await verifyToken(session.accessToken);
  if (!user) {
    // Try to refresh
    try {
      const clientSecret = env.HEARTWOOD_CLIENT_SECRET || '';
      const newTokens = await refreshAccessToken(session.refreshToken, clientSecret);

      // Update session with new tokens
      await env.SESSIONS.put(
        `session:${sessionId}`,
        JSON.stringify({
          userId: session.userId,
          accessToken: newTokens.access_token,
          refreshToken: newTokens.refresh_token,
          createdAt: Date.now(),
        }),
        { expirationTtl: newTokens.expires_in }
      );

      return { userId: session.userId, accessToken: newTokens.access_token };
    } catch {
      // Refresh failed, session invalid
      await deleteSession(env, sessionId);
      return null;
    }
  }

  return { userId: session.userId, accessToken: session.accessToken };
}
