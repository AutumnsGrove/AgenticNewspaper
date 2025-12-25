<script lang="ts">
	import '../app.css';
	import '$lib/styles/fonts.css';
	import { onMount } from 'svelte';
	import { theme, loading, error, preferences } from '$stores';

	let { children } = $props();

	onMount(() => {
		theme.init();

		// Apply font preferences
		const bodyFont = $preferences.bodyFont || 'lexend';
		const headingFont = $preferences.headingFont || 'calistoga';
		document.documentElement.setAttribute('data-body-font', bodyFont);
		document.documentElement.setAttribute('data-heading-font', headingFont);
	});

	// Watch for font changes
	$effect(() => {
		if (typeof document !== 'undefined') {
			const bodyFont = $preferences.bodyFont || 'lexend';
			const headingFont = $preferences.headingFont || 'calistoga';
			document.documentElement.setAttribute('data-body-font', bodyFont);
			document.documentElement.setAttribute('data-heading-font', headingFont);
		}
	});
</script>

<svelte:head>
	<title>The Daily Clearing</title>
	<meta name="description" content="AI-powered personalized news digest in HN style" />
</svelte:head>

<!-- Loading overlay -->
{#if $loading.isLoading}
	<div class="fixed inset-0 bg-paper-50/80 dark:bg-ink-950/80 z-50 flex items-center justify-center">
		<div class="text-center">
			<div class="animate-spin w-12 h-12 border-4 border-ink-300 dark:border-paper-700 border-t-blue-500 rounded-full mx-auto"></div>
			<p class="mt-4 text-ink-600 dark:text-paper-400">{$loading.message}</p>
			{#if $loading.progress !== undefined}
				<div class="mt-2 w-48 h-2 bg-paper-200 dark:bg-ink-800 rounded-full overflow-hidden">
					<div
						class="h-full bg-blue-500 transition-all duration-300"
						style="width: {$loading.progress}%"
					></div>
				</div>
			{/if}
		</div>
	</div>
{/if}

<!-- Error toast -->
{#if $error}
	<div class="fixed bottom-4 right-4 z-50 max-w-md">
		<div class="bg-red-500 text-white p-4 rounded-lg shadow-lg flex items-start gap-3">
			<span class="flex-1">{$error}</span>
			<button
				onclick={() => error.clear()}
				class="text-white/80 hover:text-white"
				aria-label="Dismiss"
			>
				&times;
			</button>
		</div>
	</div>
{/if}

<div class="min-h-screen">
	{@render children()}
</div>
