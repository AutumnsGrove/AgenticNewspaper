import { redirect } from '@sveltejs/kit';
import { logout } from '$lib/auth/groveauth';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ cookies }) => {
	const accessToken = cookies.get('access_token');

	if (accessToken) {
		await logout(accessToken).catch(() => {}); // Best effort
	}

	cookies.delete('access_token', { path: '/' });
	cookies.delete('refresh_token', { path: '/' });

	throw redirect(302, '/');
};
