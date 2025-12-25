<script lang="ts">
	import ArticleCard from './ArticleCard.svelte';
	import { ChevronRight } from 'lucide-svelte';
	import type { DigestSection } from '$types';

	let { section, showInsights = true, showSkeptic = true } = $props<{
		section: DigestSection;
		showInsights?: boolean;
		showSkeptic?: boolean;
	}>();

	// Get topic icon (could be extended with custom icons per topic)
	function getTopicEmoji(topic: string): string {
		const topicMap: Record<string, string> = {
			'AI & Machine Learning': '',
			'Science Breakthroughs': '',
			'Cybersecurity': '',
			'Programming & Dev Tools': '',
			'Startups & Business': '',
			'Climate & Environment': '',
			'Space & Astronomy': '',
			'Health & Medicine': '',
			'Economics & Finance': ''
		};
		return topicMap[topic] || '';
	}
</script>

<section class="topic-section">
	<div class="topic-header">
		<h2 class="topic-title">{section.topic}</h2>
		<span class="text-ink-500 dark:text-paper-500 text-sm">
			{section.articles.length} article{section.articles.length !== 1 ? 's' : ''}
		</span>
	</div>

	<!-- Section summary -->
	{#if section.sectionSummary}
		<p class="text-ink-600 dark:text-paper-400 mb-6 leading-relaxed">
			{section.sectionSummary}
		</p>
	{/if}

	<!-- Articles -->
	<div class="space-y-8">
		{#each section.articles as article (article.id)}
			<ArticleCard {article} {showInsights} {showSkeptic} />
		{/each}
	</div>

	<!-- Cross-story insights -->
	{#if section.crossStoryInsights.length > 0}
		<div class="mt-8 p-4 bg-purple-50 dark:bg-purple-900/20 border-l-4 border-purple-500 rounded-r">
			<h3 class="font-semibold text-purple-700 dark:text-purple-400 mb-2 flex items-center gap-2">
				<ChevronRight class="w-4 h-4" />
				Cross-Story Insights
			</h3>
			<ul class="space-y-2">
				{#each section.crossStoryInsights as insight}
					<li class="text-sm text-ink-700 dark:text-paper-300">{insight}</li>
				{/each}
			</ul>
		</div>
	{/if}
</section>
