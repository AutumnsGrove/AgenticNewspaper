<script lang="ts">
	import { FileText, Zap, DollarSign, Clock, TrendingUp, AlertTriangle } from 'lucide-svelte';
	import type { DigestMetadata } from '$types';

	let { metadata } = $props<{
		metadata: DigestMetadata;
	}>();

	function formatCost(cost: number): string {
		return cost < 0.01 ? '<$0.01' : `$${cost.toFixed(2)}`;
	}

	function formatTime(seconds: number): string {
		if (seconds < 60) return `${Math.round(seconds)}s`;
		return `${Math.round(seconds / 60)}m ${Math.round(seconds % 60)}s`;
	}

	function formatNumber(num: number): string {
		if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
		if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
		return num.toString();
	}
</script>

<footer class="digest-stats">
	<div class="stat-item">
		<div class="stat-value flex items-center justify-center gap-2">
			<FileText class="w-5 h-5 text-blue-500" />
			{metadata.totalArticlesIncluded}
		</div>
		<div class="stat-label">Articles</div>
	</div>

	<div class="stat-item">
		<div class="stat-value flex items-center justify-center gap-2">
			<TrendingUp class="w-5 h-5 text-green-500" />
			{metadata.topicsCovered.length}
		</div>
		<div class="stat-label">Topics</div>
	</div>

	<div class="stat-item">
		<div class="stat-value flex items-center justify-center gap-2">
			<Zap class="w-5 h-5 text-amber-500" />
			{formatNumber(metadata.totalTokensUsed)}
		</div>
		<div class="stat-label">Tokens</div>
	</div>

	<div class="stat-item">
		<div class="stat-value flex items-center justify-center gap-2">
			<DollarSign class="w-5 h-5 text-purple-500" />
			{formatCost(metadata.totalCostUsd)}
		</div>
		<div class="stat-label">Cost</div>
	</div>
</footer>

<!-- Additional metadata -->
<div class="mt-6 text-center text-xs text-ink-500 dark:text-paper-500">
	<p>
		Scanned {metadata.totalArticlesFound} articles &middot;
		Parsed {metadata.totalArticlesParsed} &middot;
		Included {metadata.totalArticlesIncluded}
	</p>
	<p class="mt-1">
		Generated in {formatTime(metadata.processingTimeSeconds)} on {new Date(metadata.generatedAt).toLocaleString()}
	</p>
</div>
