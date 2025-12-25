<script lang="ts">
	import { ExternalLink, Clock, Star, AlertTriangle, Lightbulb, ThumbsUp, ThumbsDown } from 'lucide-svelte';
	import type { Article } from '$types';

	let { article, showInsights = true, showSkeptic = true } = $props<{
		article: Article;
		showInsights?: boolean;
		showSkeptic?: boolean;
	}>();

	function formatScore(score: number): string {
		return `${Math.round(score * 100)}%`;
	}

	function getBiasLabel(direction: Article['biasDirection']): string {
		const labels: Record<Article['biasDirection'], string> = {
			left: 'Left-Leaning',
			center_left: 'Center-Left',
			center: 'Balanced',
			center_right: 'Center-Right',
			right: 'Right-Leaning',
			unknown: 'Unknown'
		};
		return labels[direction];
	}

	function getBiasColor(direction: Article['biasDirection']): string {
		if (direction === 'center') return 'text-green-600 dark:text-green-400';
		if (direction === 'unknown') return 'text-ink-500 dark:text-paper-500';
		return 'text-amber-600 dark:text-amber-400';
	}
</script>

<article class="article-card group">
	<!-- Title and link -->
	<a href={article.url} target="_blank" rel="noopener noreferrer" class="block">
		<h3 class="article-title group-hover:underline flex items-start gap-2">
			<span>{article.title}</span>
			<ExternalLink class="w-4 h-4 flex-shrink-0 mt-1 opacity-0 group-hover:opacity-100 transition-opacity" />
		</h3>
	</a>

	<!-- Metadata -->
	<div class="article-meta">
		<span class="font-medium">{article.source}</span>
		{#if article.author}
			<span>&middot;</span>
			<span>{article.author}</span>
		{/if}
		<span>&middot;</span>
		<span class="flex items-center gap-1">
			<Clock class="w-3 h-3" />
			{article.readingTimeMinutes} min
		</span>
		<span>&middot;</span>
		<span class="flex items-center gap-1 {getBiasColor(article.biasDirection)}">
			{getBiasLabel(article.biasDirection)}
		</span>
	</div>

	<!-- Summary -->
	<p class="article-summary">{article.summary}</p>

	<!-- Key Points -->
	{#if article.keyPoints.length > 0}
		<ul class="mt-3 space-y-1">
			{#each article.keyPoints.slice(0, 3) as point}
				<li class="flex items-start gap-2 text-sm text-ink-600 dark:text-paper-400">
					<span class="text-ink-400 dark:text-paper-600">&bull;</span>
					<span>{point}</span>
				</li>
			{/each}
		</ul>
	{/if}

	<!-- Why it matters -->
	{#if showInsights && article.whyMatters}
		<div class="article-insights">
			<div class="article-insights-title flex items-center gap-2">
				<Lightbulb class="w-4 h-4" />
				Why it matters
			</div>
			<p>{article.whyMatters}</p>
		</div>
	{/if}

	<!-- Technical insights -->
	{#if showInsights && article.technicalInsights.length > 0}
		<div class="mt-3 flex flex-wrap gap-2">
			{#each article.technicalInsights.slice(0, 2) as insight}
				<span class="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">
					{insight}
				</span>
			{/each}
		</div>
	{/if}

	<!-- Skeptic's corner -->
	{#if showSkeptic && article.skepticsCorner}
		<div class="skeptics-corner">
			<div class="skeptics-corner-title flex items-center gap-2">
				<AlertTriangle class="w-4 h-4" />
				Skeptic's Corner
			</div>
			<p>{article.skepticsCorner}</p>
		</div>
	{/if}

	<!-- Red flags -->
	{#if article.redFlags.length > 0}
		<div class="mt-3 flex flex-wrap gap-2">
			{#each article.redFlags as flag}
				<span class="text-xs px-2 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded flex items-center gap-1">
					<AlertTriangle class="w-3 h-3" />
					{flag}
				</span>
			{/each}
		</div>
	{/if}

	<!-- Quality scores (compact) -->
	<div class="mt-4 flex items-center gap-4 text-xs text-ink-500 dark:text-paper-500">
		<span class="flex items-center gap-1">
			<Star class="w-3 h-3" />
			Quality: {formatScore(article.qualityScore)}
		</span>
		<span>Relevance: {formatScore(article.relevanceScore)}</span>
		<span>Novelty: {formatScore(article.noveltyScore)}</span>
	</div>

	<!-- Feedback buttons -->
	<div class="mt-4 flex items-center gap-2">
		<button class="btn btn-ghost text-sm" aria-label="Like article">
			<ThumbsUp class="w-4 h-4" />
		</button>
		<button class="btn btn-ghost text-sm" aria-label="Dislike article">
			<ThumbsDown class="w-4 h-4" />
		</button>
	</div>
</article>
