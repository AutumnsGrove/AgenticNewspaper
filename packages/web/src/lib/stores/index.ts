/**
 * Svelte stores for The Daily Clearing.
 */

import { writable, derived, type Readable } from 'svelte/store';
import type { Digest, User, UserPreferences } from '$types';

// Theme store
function createThemeStore() {
	const { subscribe, set, update } = writable<'light' | 'dark'>('light');

	return {
		subscribe,
		toggle: () => update((theme) => {
			const newTheme = theme === 'light' ? 'dark' : 'light';
			if (typeof window !== 'undefined') {
				localStorage.setItem('theme', newTheme);
				document.documentElement.classList.toggle('dark', newTheme === 'dark');
			}
			return newTheme;
		}),
		set: (theme: 'light' | 'dark') => {
			set(theme);
			if (typeof window !== 'undefined') {
				localStorage.setItem('theme', theme);
				document.documentElement.classList.toggle('dark', theme === 'dark');
			}
		},
		init: () => {
			if (typeof window !== 'undefined') {
				const saved = localStorage.getItem('theme');
				const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
				const theme = (saved as 'light' | 'dark') || (prefersDark ? 'dark' : 'light');
				set(theme);
				document.documentElement.classList.toggle('dark', theme === 'dark');
			}
		}
	};
}

export const theme = createThemeStore();

// User store
function createUserStore() {
	const { subscribe, set, update } = writable<User | null>(null);

	return {
		subscribe,
		set,
		login: (user: User) => set(user),
		logout: () => set(null),
		update: (data: Partial<User>) => update((user) => (user ? { ...user, ...data } : null))
	};
}

export const user = createUserStore();

// User preferences store
function createPreferencesStore() {
	const defaultPreferences: UserPreferences = {
		topics: [
			{ name: 'AI & Machine Learning', keywords: ['AI', 'LLM', 'machine learning'], priority: 1, enabled: true },
			{ name: 'Science Breakthroughs', keywords: ['research', 'discovery'], priority: 2, enabled: true }
		],
		deliveryFrequency: 'daily',
		deliveryTime: '06:00',
		channels: ['web'],
		style: {
			tone: 'hn-style',
			skepticismLevel: 3,
			technicalDepth: 3,
			includeBiasAnalysis: true,
			includeCrossConnections: true
		}
	};

	const { subscribe, set, update } = writable<UserPreferences>(defaultPreferences);

	return {
		subscribe,
		set,
		update: (data: Partial<UserPreferences>) => update((prefs) => ({ ...prefs, ...data })),
		addTopic: (topic: UserPreferences['topics'][0]) =>
			update((prefs) => ({ ...prefs, topics: [...prefs.topics, topic] })),
		removeTopic: (name: string) =>
			update((prefs) => ({ ...prefs, topics: prefs.topics.filter((t) => t.name !== name) })),
		toggleTopic: (name: string) =>
			update((prefs) => ({
				...prefs,
				topics: prefs.topics.map((t) => (t.name === name ? { ...t, enabled: !t.enabled } : t))
			})),
		reset: () => set(defaultPreferences)
	};
}

export const preferences = createPreferencesStore();

// Current digest store
function createDigestStore() {
	const { subscribe, set, update } = writable<Digest | null>(null);

	return {
		subscribe,
		set,
		clear: () => set(null),
		setFromApi: (data: Digest) => set(data)
	};
}

export const currentDigest = createDigestStore();

// Digest history store
function createDigestHistoryStore() {
	const { subscribe, set, update } = writable<Digest[]>([]);

	return {
		subscribe,
		set,
		add: (digest: Digest) => update((digests) => [digest, ...digests].slice(0, 30)),
		clear: () => set([])
	};
}

export const digestHistory = createDigestHistoryStore();

// Loading state store
function createLoadingStore() {
	const { subscribe, set, update } = writable<{
		isLoading: boolean;
		message: string;
		progress?: number;
	}>({
		isLoading: false,
		message: ''
	});

	return {
		subscribe,
		start: (message = 'Loading...') => set({ isLoading: true, message }),
		progress: (progress: number, message?: string) =>
			update((state) => ({ ...state, progress, message: message || state.message })),
		stop: () => set({ isLoading: false, message: '' })
	};
}

export const loading = createLoadingStore();

// Error store
function createErrorStore() {
	const { subscribe, set } = writable<string | null>(null);

	return {
		subscribe,
		set: (error: string | null) => set(error),
		clear: () => set(null)
	};
}

export const error = createErrorStore();

// Derived stores
export const isAuthenticated: Readable<boolean> = derived(user, ($user) => $user !== null);

export const enabledTopics: Readable<UserPreferences['topics']> = derived(
	preferences,
	($preferences) => $preferences.topics.filter((t) => t.enabled)
);

export const articleCount: Readable<number> = derived(currentDigest, ($digest) => {
	if (!$digest) return 0;
	return $digest.sections.reduce((acc, section) => acc + section.articles.length, 0);
});
