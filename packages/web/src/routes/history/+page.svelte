<script lang="ts">
	import { digestHistory } from '$stores';
	import { Masthead } from '$components';
	import { Calendar } from 'lucide-svelte';
</script>

<Masthead />

<main class="max-w-4xl mx-auto px-4 py-8">
	<div class="mb-8">
		<h1 class="text-3xl font-serif font-bold text-ink-900 dark:text-paper-100">
			Digest History
		</h1>
		<p class="text-ink-600 dark:text-paper-400 mt-2">
			View your previously generated digests
		</p>
	</div>

	{#if $digestHistory.length === 0}
		<div class="text-center py-16">
			<Calendar class="w-16 h-16 mx-auto text-ink-300 dark:text-paper-600 mb-4" />
			<h2 class="text-xl font-semibold text-ink-700 dark:text-paper-300 mb-2">
				No digest history yet
			</h2>
			<p class="text-ink-500 dark:text-paper-500 mb-6">
				Generate your first digest to see it appear here
			</p>
			<a
				href="/"
				class="inline-block px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
			>
				Go to Home
			</a>
		</div>
	{:else}
		<div class="space-y-6">
			{#each $digestHistory as digest}
				<article class="border border-ink-200 dark:border-paper-700 rounded-lg p-6 hover:shadow-md transition-shadow">
					<div class="flex items-start justify-between mb-4">
						<div>
							<h2 class="text-xl font-serif font-bold text-ink-900 dark:text-paper-100 mb-1">
								{digest.metadata.generatedAt.split('T')[0]}
							</h2>
							<p class="text-sm text-ink-600 dark:text-paper-400">
								{digest.sections.length} topics • {digest.metadata.totalArticlesIncluded} articles
							</p>
						</div>
						<div class="text-right">
							<div class="text-sm text-ink-500 dark:text-paper-500">
								${digest.metadata.totalCostUsd.toFixed(2)}
							</div>
							<div class="text-xs text-ink-400 dark:text-paper-600">
								{(digest.metadata.totalTokensUsed / 1000).toFixed(1)}K tokens
							</div>
						</div>
					</div>

					<div class="flex flex-wrap gap-2 mb-4">
						{#each digest.sections.slice(0, 5) as section}
							<span class="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs rounded">
								{section.topic}
							</span>
						{/each}
						{#if digest.sections.length > 5}
							<span class="px-2 py-1 text-ink-500 dark:text-paper-500 text-xs">
								+{digest.sections.length - 5} more
							</span>
						{/if}
					</div>

					<a
						href="/?digest={digest.metadata.digestId}"
						class="text-blue-600 dark:text-blue-400 hover:underline text-sm font-medium"
					>
						View Full Digest →
					</a>
				</article>
			{/each}
		</div>
	{/if}
</main>
