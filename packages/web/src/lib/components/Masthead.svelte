<script lang="ts">
	import { Sun, Moon, Rss, Settings } from 'lucide-svelte';
	import { theme } from '$stores';

	let { date = new Date().toLocaleDateString('en-US', {
		weekday: 'long',
		year: 'numeric',
		month: 'long',
		day: 'numeric'
	}), volume = 1, issue = 1 } = $props<{
		date?: string;
		volume?: number;
		issue?: number;
	}>();

	function toggleTheme() {
		theme.toggle();
		if (typeof document !== 'undefined') {
			document.documentElement.classList.toggle('dark');
			localStorage.setItem('theme', $theme === 'light' ? 'dark' : 'light');
		}
	}
</script>

<header class="masthead">
	<div class="flex items-center justify-between mb-4">
		<div class="flex items-center gap-2">
			<button onclick={toggleTheme} class="theme-toggle" aria-label="Toggle theme">
				{#if $theme === 'light'}
					<Moon class="w-5 h-5" />
				{:else}
					<Sun class="w-5 h-5" />
				{/if}
			</button>
		</div>

		<div class="flex items-center gap-2">
			<a href="/rss" class="theme-toggle" aria-label="RSS Feed">
				<Rss class="w-5 h-5" />
			</a>
			<a href="/settings" class="theme-toggle" aria-label="Settings">
				<Settings class="w-5 h-5" />
			</a>
		</div>
	</div>

	<h1 class="masthead-title">The Daily Clearing</h1>

	<div class="masthead-date">
		{date} &middot; Vol. {volume}, No. {issue}
	</div>

	<p class="text-center text-ink-600 dark:text-paper-400 text-sm mt-4 max-w-2xl mx-auto">
		AI-powered news synthesis with technical depth and healthy skepticism
	</p>
</header>
