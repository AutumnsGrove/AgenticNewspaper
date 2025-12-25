import { redirect } from '@sveltejs/kit';
import { generateCodeVerifier, generateCodeChallenge, getLoginUrl } from '$lib/auth/groveauth';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ cookies, platform }) => {
	const state = crypto.randomUUID();
	const codeVerifier = generateCodeVerifier();
	const codeChallenge = await generateCodeChallenge(codeVerifier);

	// Get env vars from platform (Cloudflare Pages)
	const clientId = platform?.env?.GROVEAUTH_CLIENT_ID || 'daily-clearing';
	const redirectUri = platform?.env?.GROVEAUTH_REDIRECT_URI || 'https://clearing.autumnsgrove.com/auth/callback';

	// Store for callback verification
	cookies.set('auth_state', state, {
		path: '/',
		httpOnly: true,
		secure: true,
		sameSite: 'lax',
		maxAge: 600 // 10 minutes
	});
	cookies.set('code_verifier', codeVerifier, {
		path: '/',
		httpOnly: true,
		secure: true,
		sameSite: 'lax',
		maxAge: 600
	});

	const loginUrl = getLoginUrl({
		clientId,
		redirectUri,
		state,
		codeChallenge
	});

	throw redirect(302, loginUrl);
};
