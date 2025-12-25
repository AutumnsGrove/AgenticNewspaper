// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		interface Error {}
		interface Locals {
			user: {
				id: string;
				email: string;
				name: string | null;
			} | null;
		}
		interface PageData {}
		interface PageState {}
		interface Platform {
			env?: {
				GROVEAUTH_CLIENT_ID?: string;
				GROVEAUTH_CLIENT_SECRET?: string;
				GROVEAUTH_REDIRECT_URI?: string;
			};
		}
	}
}

export {};
