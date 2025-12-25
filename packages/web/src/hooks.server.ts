import type { Handle } from '@sveltejs/kit';
import { verifyToken, refreshTokens } from '$lib/auth/groveauth';

export const handle: Handle = async ({ event, resolve }) => {
	const accessToken = event.cookies.get('access_token');
	const refreshToken = event.cookies.get('refresh_token');

	event.locals.user = null;

	if (accessToken) {
		const tokenInfo = await verifyToken(accessToken);

		if (tokenInfo.active) {
			event.locals.user = {
				id: tokenInfo.sub!,
				email: tokenInfo.email!,
				name: tokenInfo.name || null
			};
		} else if (refreshToken) {
			// Token expired, try refresh
			const clientId = event.platform?.env?.GROVEAUTH_CLIENT_ID || 'daily-clearing';
			const clientSecret = event.platform?.env?.GROVEAUTH_CLIENT_SECRET || '';

			if (clientSecret) {
				const newTokens = await refreshTokens({
					refreshToken,
					clientId,
					clientSecret
				});

				if (newTokens) {
					event.cookies.set('access_token', newTokens.access_token, {
						path: '/',
						httpOnly: true,
						secure: true,
						sameSite: 'lax',
						maxAge: newTokens.expires_in
					});
					event.cookies.set('refresh_token', newTokens.refresh_token, {
						path: '/',
						httpOnly: true,
						secure: true,
						sameSite: 'lax',
						maxAge: 30 * 24 * 60 * 60
					});

					const newTokenInfo = await verifyToken(newTokens.access_token);
					if (newTokenInfo.active) {
						event.locals.user = {
							id: newTokenInfo.sub!,
							email: newTokenInfo.email!,
							name: newTokenInfo.name || null
						};
					}
				}
			}
		}
	}

	return resolve(event);
};
