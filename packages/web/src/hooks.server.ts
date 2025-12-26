import type { Handle } from '@sveltejs/kit';
import { validateSession } from '$lib/auth/groveauth';

/**
 * Server hook that validates Heartwood sessions on every request
 *
 * The grove_session cookie (domain: .grove.place) is automatically
 * sent with requests and validated against Heartwood's session API.
 */
export const handle: Handle = async ({ event, resolve }) => {
	// Default to no user
	event.locals.user = null;

	// Get cookie header to forward to Heartwood
	const cookieHeader = event.request.headers.get('Cookie');

	if (cookieHeader) {
		// Validate session with Heartwood
		const { valid, user } = await validateSession(cookieHeader);

		if (valid && user) {
			// Map Heartwood user to our user format
			event.locals.user = {
				id: user.id,
				email: user.email,
				name: user.name,
			};
		}
	}

	return resolve(event);
};
