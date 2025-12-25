import { redirect, error } from '@sveltejs/kit';
import { exchangeCode } from '$lib/auth/groveauth';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ url, cookies, platform }) => {
	const code = url.searchParams.get('code');
	const state = url.searchParams.get('state');
	const authError = url.searchParams.get('error');

	if (authError) {
		throw error(400, `Authentication failed: ${authError}`);
	}

	if (!code || !state) {
		throw error(400, 'Missing code or state');
	}

	// Verify state
	const savedState = cookies.get('auth_state');
	console.log('Callback state verification:', { receivedState: state, savedState });

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

	// Get env vars from platform
	const clientId = platform?.env?.GROVEAUTH_CLIENT_ID || 'daily-clearing';
	const clientSecret = platform?.env?.GROVEAUTH_CLIENT_SECRET || '';
	const redirectUri = platform?.env?.GROVEAUTH_REDIRECT_URI || 'https://clearing.autumnsgrove.com/auth/callback';

	if (!clientSecret) {
		throw error(500, 'GroveAuth client secret not configured');
	}

	try {
		const tokens = await exchangeCode({
			code,
			codeVerifier,
			clientId,
			clientSecret,
			redirectUri
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

		throw redirect(302, '/settings');
	} catch (err) {
		if (err instanceof Response) throw err; // Re-throw redirects
		console.error('Auth error:', err);
		throw error(500, 'Authentication failed');
	}
};
