import { redirect } from '@sveltejs/kit';
import { getLoginUrl } from '$lib/auth/groveauth';
import type { RequestHandler } from './$types';

/**
 * Login endpoint - redirects to Heartwood for authentication
 *
 * No PKCE needed! Heartwood handles the session creation and
 * sets the grove_session cookie (domain: .grove.place)
 */
export const GET: RequestHandler = async ({ platform }) => {
	const clientId = platform?.env?.GROVEAUTH_CLIENT_ID || 'daily-clearing';
	const redirectUri =
		platform?.env?.GROVEAUTH_REDIRECT_URI ||
		'https://clearing.autumnsgrove.com/auth/callback';

	const loginUrl = getLoginUrl({
		clientId,
		redirectUri,
	});

	throw redirect(302, loginUrl);
};
