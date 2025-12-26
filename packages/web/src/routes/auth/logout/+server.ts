import { redirect } from '@sveltejs/kit';
import { revokeSession } from '$lib/auth/groveauth';
import type { RequestHandler } from './$types';

/**
 * Logout endpoint - revokes the current session
 *
 * This revokes only the current device's session.
 * The user will remain logged in on other devices.
 */
export const POST: RequestHandler = async ({ request }) => {
	const cookieHeader = request.headers.get('Cookie');

	if (cookieHeader) {
		// Revoke the current session at Heartwood
		await revokeSession(cookieHeader).catch(() => {
			// Best effort - continue even if revocation fails
		});
	}

	// Redirect to home page
	throw redirect(302, '/');
};
