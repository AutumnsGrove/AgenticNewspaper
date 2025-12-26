import { redirect, error } from '@sveltejs/kit';
import { exchangeCode } from '$lib/auth/groveauth';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ url, cookies, platform }) => {
	const requestId = crypto.randomUUID().slice(0, 8);
	console.log(`[${requestId}] Auth callback invoked`, { url: url.toString() });

	const code = url.searchParams.get('code');
	const state = url.searchParams.get('state');
	const authError = url.searchParams.get('error');

	if (authError) {
		console.log(`[${requestId}] OAuth error received:`, authError);
		throw error(400, `Authentication failed: ${authError}`);
	}

	if (!code || !state) {
		console.log(`[${requestId}] Missing parameters:`, { hasCode: !!code, hasState: !!state });
		throw error(400, 'Missing code or state');
	}

	// Verify state
	const savedState = cookies.get('auth_state');
	console.log(`[${requestId}] State verification:`, { receivedState: state, savedState });

	if (!savedState) {
		throw error(400, 'No saved state found - cookie may have expired or not been set');
	}

	if (state !== savedState) {
		throw error(400, `State mismatch - received: ${state}, expected: ${savedState}`);
	}

	const codeVerifier = cookies.get('code_verifier');
	if (!codeVerifier) {
		throw error(400, 'Missing code verifier');
	}

	// Clear auth cookies
	cookies.delete('auth_state', { path: '/' });
	cookies.delete('code_verifier', { path: '/' });
	console.log(`[${requestId}] Cleared OAuth state cookies`);

	// Get env vars from platform
	const clientId = platform?.env?.GROVEAUTH_CLIENT_ID || 'daily-clearing';
	const clientSecret = platform?.env?.GROVEAUTH_CLIENT_SECRET || '';
	const redirectUri = platform?.env?.GROVEAUTH_REDIRECT_URI || 'https://clearing.autumnsgrove.com/auth/callback';

	console.log(`[${requestId}] Token exchange config:`, {
		clientId,
		hasClientSecret: !!clientSecret,
		redirectUri,
		codeLength: code.length,
		codeVerifierLength: codeVerifier.length
	});

	if (!clientSecret) {
		console.log(`[${requestId}] ERROR: Client secret not configured`);
		throw error(500, 'GroveAuth client secret not configured');
	}

	try {
		console.log(`[${requestId}] Starting token exchange...`);
		const tokens = await exchangeCode({
			code,
			codeVerifier,
			clientId,
			clientSecret,
			redirectUri
		});

		console.log(`[${requestId}] ✓ Token exchange successful`, {
			hasAccessToken: !!tokens.access_token,
			hasRefreshToken: !!tokens.refresh_token,
			expiresIn: tokens.expires_in
		});

		// Set token cookies
		cookies.set('access_token', tokens.access_token, {
			path: '/',
			httpOnly: true,
			secure: true,
			sameSite: 'lax',
			maxAge: tokens.expires_in
		});

		cookies.set('refresh_token', tokens.refresh_token, {
			path: '/',
			httpOnly: true,
			secure: true,
			sameSite: 'lax',
			maxAge: 30 * 24 * 60 * 60 // 30 days
		});

		console.log(`[${requestId}] ✓ Cookies set, redirecting to /settings`);
		throw redirect(302, '/settings');
	} catch (err) {
		if (err instanceof Response) {
			console.log(`[${requestId}] ✓ Redirect response, re-throwing`);
			throw err;
		}

		console.error(`[${requestId}] ✗ Token exchange failed:`, {
			errorType: err?.constructor?.name,
			errorMessage: err instanceof Error ? err.message : String(err),
			errorStack: err instanceof Error ? err.stack : undefined
		});

		// Show the actual error message for debugging
		const errorMessage = err instanceof Error ? err.message : 'Authentication failed';
		throw error(500, `Authentication failed: ${errorMessage}`);
	}
};
