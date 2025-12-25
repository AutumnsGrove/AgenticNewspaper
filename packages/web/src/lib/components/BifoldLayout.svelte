<script lang="ts">
	import TopicSection from './TopicSection.svelte';
	import type { DigestSection } from '$types';

	let { sections, showInsights = true, showSkeptic = true } = $props<{
		sections: DigestSection[];
		showInsights?: boolean;
		showSkeptic?: boolean;
	}>();

	// Split sections into two columns for bifold layout
	function splitSections(sections: DigestSection[]): [DigestSection[], DigestSection[]] {
		const left: DigestSection[] = [];
		const right: DigestSection[] = [];

		let leftCount = 0;
		let rightCount = 0;

		for (const section of sections) {
			// Balance by article count
			if (leftCount <= rightCount) {
				left.push(section);
				leftCount += section.articles.length;
			} else {
				right.push(section);
				rightCount += section.articles.length;
			}
		}

		return [left, right];
	}

	let [leftSections, rightSections] = $derived(splitSections(sections));
</script>

<div class="bifold-container relative">
	<!-- Left column -->
	<div class="bifold-column">
		{#each leftSections as section (section.topic)}
			<TopicSection {section} {showInsights} {showSkeptic} />
		{/each}
	</div>

	<!-- Center divider (desktop only) -->
	<div class="bifold-divider" aria-hidden="true"></div>

	<!-- Right column -->
	<div class="bifold-column">
		{#each rightSections as section (section.topic)}
			<TopicSection {section} {showInsights} {showSkeptic} />
		{/each}
	</div>
</div>
