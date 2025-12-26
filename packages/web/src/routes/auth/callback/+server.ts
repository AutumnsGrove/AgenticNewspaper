import { redirect } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

/**
 * OAuth callback handler
 *
 * Heartwood has already:
 * 1. Authenticated the user
 * 2. Created a session
 * 3. Set the grove_session cookie (domain: .grove.place)
 *
 * We just need to redirect the user to their destination!
 */
export const GET: RequestHandler = async () => {
	// Session cookie is already set by Heartwood
	// Just redirect to settings
	throw redirect(302, '/settings');
};
