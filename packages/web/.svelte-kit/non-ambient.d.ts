
// this file is generated — do not edit it


declare module "svelte/elements" {
	export interface HTMLAttributes<T> {
		'data-sveltekit-keepfocus'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-noscroll'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-preload-code'?:
			| true
			| ''
			| 'eager'
			| 'viewport'
			| 'hover'
			| 'tap'
			| 'off'
			| undefined
			| null;
		'data-sveltekit-preload-data'?: true | '' | 'hover' | 'tap' | 'off' | undefined | null;
		'data-sveltekit-reload'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-replacestate'?: true | '' | 'off' | undefined | null;
	}
}

export {};


declare module "$app/types" {
	export interface AppTypes {
		RouteId(): "/" | "/auth" | "/auth/callback" | "/auth/login" | "/auth/logout" | "/history" | "/settings";
		RouteParams(): {
			
		};
		LayoutParams(): {
			"/": Record<string, never>;
			"/auth": Record<string, never>;
			"/auth/callback": Record<string, never>;
			"/auth/login": Record<string, never>;
			"/auth/logout": Record<string, never>;
			"/history": Record<string, never>;
			"/settings": Record<string, never>
		};
		Pathname(): "/" | "/auth" | "/auth/" | "/auth/callback" | "/auth/callback/" | "/auth/login" | "/auth/login/" | "/auth/logout" | "/auth/logout/" | "/history" | "/history/" | "/settings" | "/settings/";
		ResolvedPathname(): `${"" | `/${string}`}${ReturnType<AppTypes['Pathname']>}`;
		Asset(): "/fonts/AtkinsonHyperlegible-Regular.ttf" | "/fonts/Calistoga-Regular.ttf" | "/fonts/Lexend-Regular.ttf" | "/fonts/Lora-Regular.ttf" | "/fonts/OpenDyslexic-Regular.otf" | string & {};
	}
}