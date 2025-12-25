<script lang="ts">
	import { Masthead, BifoldLayout, DigestStats } from '$components';
	import { currentDigest, loading, error, preferences } from '$stores';
	import { RefreshCw, Calendar, ChevronRight, Settings, LogIn, LogOut } from 'lucide-svelte';
	import type { Digest } from '$types';
	import { generateTestDigest } from '$lib/api';

	let { data } = $props();

	// Mock data for development
	const mockDigest: Digest = {
		metadata: {
			digestId: '2025-12-25',
			generatedAt: new Date().toISOString(),
			topicsCovered: ['AI & Machine Learning', 'Science Breakthroughs'],
			totalArticlesFound: 847,
			totalArticlesParsed: 156,
			totalArticlesIncluded: 12,
			totalTokensUsed: 45000,
			totalCostUsd: 0.035,
			processingTimeSeconds: 45.2
		},
		sections: [
			{
				topic: 'AI & Machine Learning',
				sectionSummary: 'This week saw major developments in efficient inference and open-source model releases, with DeepSeek continuing to push cost boundaries.',
				articles: [
					{
						id: '1',
						url: 'https://arxiv.org/example-1',
						title: 'DeepSeek V3.2 Benchmarks Show 90% Cost Reduction',
						source: 'arxiv.org',
						author: 'DeepSeek Team',
						publishedDate: '2025-12-24',
						wordCount: 2500,
						readingTimeMinutes: 11,
						relevanceScore: 0.92,
						qualityScore: 0.88,
						noveltyScore: 0.85,
						biasScore: 0.5,
						technicalLevel: 4,
						summary: 'The Chinese AI lab\'s latest release activates only 37B of its 685B parameters during inference, achieving GPT-4 class performance at a fraction of the cost. The paper details a novel sparse attention mechanism.',
						keyPoints: [
							'37B active parameters from 685B total using Mixture of Experts',
							'Achieves 95% of GPT-4 performance on key benchmarks',
							'Training cost estimated at $5.6M (vs $100M+ for GPT-4)'
						],
						whyMatters: 'Cost democratization could reshape the AI landscape, enabling smaller players to compete with tech giants on model capability.',
						technicalInsights: ['MoE architecture', 'Sparse attention'],
						biasDirection: 'center',
						skepticsCorner: 'Benchmark gaming is rampant in AI. Real-world performance on complex reasoning tasks remains to be seen. The training data composition is also undisclosed.',
						redFlags: []
					},
					{
						id: '2',
						url: 'https://arstechnica.com/example-2',
						title: 'Claude Opus 4.5 Debuts Extended Thinking for Complex Tasks',
						source: 'arstechnica.com',
						author: 'Kyle Orland',
						publishedDate: '2025-12-23',
						wordCount: 1800,
						readingTimeMinutes: 8,
						relevanceScore: 0.89,
						qualityScore: 0.82,
						noveltyScore: 0.78,
						biasScore: 0.52,
						technicalLevel: 3,
						summary: 'Anthropic\'s new flagship model introduces "extended thinking" - visible chain-of-thought reasoning that improves accuracy on multi-step problems by 23%.',
						keyPoints: [
							'Extended thinking shows reasoning process in real-time',
							'23% improvement on complex math and coding tasks',
							'Available through API with new thinking_budget parameter'
						],
						whyMatters: 'Visible reasoning makes AI systems more auditable and helps users understand model limitations.',
						technicalInsights: ['Chain-of-thought', 'Process supervision'],
						biasDirection: 'center',
						redFlags: []
					}
				],
				crossStoryInsights: [
					'Both developments point to a shift from scaling parameters to scaling inference compute',
					'The race between open-source and proprietary models is heating up in the reasoning space'
				]
			},
			{
				topic: 'Science Breakthroughs',
				sectionSummary: 'Promising developments in room-temperature superconductors and quantum computing error correction dominated science news.',
				articles: [
					{
						id: '3',
						url: 'https://nature.com/example-3',
						title: 'New Superconductor Candidate Shows Promise at Higher Temperatures',
						source: 'nature.com',
						author: 'Research Team',
						publishedDate: '2025-12-22',
						wordCount: 3200,
						readingTimeMinutes: 14,
						relevanceScore: 0.85,
						qualityScore: 0.91,
						noveltyScore: 0.88,
						biasScore: 0.5,
						technicalLevel: 5,
						summary: 'A hydride compound shows superconducting properties at -20°C under 100 GPa pressure. While still requiring extreme pressure, this represents significant progress toward practical applications.',
						keyPoints: [
							'Superconductivity observed at -20°C (253K)',
							'Requires 100 GPa pressure (vs 267 GPa in previous work)',
							'Crystal structure confirmed via X-ray diffraction'
						],
						whyMatters: 'Reducing pressure requirements is key to making superconductors practical. This is incremental but meaningful progress.',
						technicalInsights: ['Hydrogen-rich compounds', 'High-pressure synthesis'],
						biasDirection: 'center',
						skepticsCorner: 'Previous "breakthroughs" in this field have failed replication. The extreme pressure requirement still makes this impractical. Let\'s see if other labs can reproduce.',
						redFlags: ['Awaiting independent replication']
					}
				],
				crossStoryInsights: []
			}
		],
		crossStoryConnections: 'The cost reduction in AI inference and the superconductor research progress suggest a broader trend toward more efficient computational methods across fields.',
		skepticsSummary: 'This week\'s digest contains several exciting announcements, but readers should note that AI benchmarks are increasingly gamed, and superconductor claims have a poor track record. Healthy skepticism is warranted.'
	};

	// Use mock data for now
	let digest = $derived($currentDigest || mockDigest);

	async function refreshDigest() {
		const mode = $preferences.generationMode || 'cloudflare';

		try {
			if (mode === 'cloudflare') {
				// Cloudflare mode requires authentication (not yet implemented)
				alert(
					'🔐 Cloudflare mode requires authentication.\n\n' +
					'For now, please switch to Server mode in Settings to generate digests.\n\n' +
					'Server mode provisions an ephemeral Hetzner VPS that self-destructs after generation.'
				);
				return;
			}

			// Server mode - provision Hetzner server
			loading.start('Provisioning ephemeral server...');

			const result = await generateTestDigest();

			if (result.success) {
				loading.start(`Server provisioned! Job ID: ${result.data?.jobId.slice(0, 8)}...`);
				loading.progress(50, 'Server booting and generating digest...');

				// TODO: Poll job status and update when complete
				await new Promise((resolve) => setTimeout(resolve, 3000));
				loading.progress(100, 'Digest generated!');
				await new Promise((resolve) => setTimeout(resolve, 1000));
				loading.stop();

				console.log('🎉 Digest generation started!', result.data);
				alert(
					`✅ Digest generation started!\n\n` +
					`Job ID: ${result.data?.jobId}\n` +
					`Server: ${result.data?.serverId}\n` +
					`IP: ${result.data?.serverIp}\n\n` +
					`The server is now generating your digest. This typically takes 30-60 seconds.`
				);
			} else {
				error.set(result.error?.message || 'Failed to start digest generation');
				loading.stop();
			}
		} catch (err) {
			error.set('Failed to connect to API');
			loading.stop();
		}
	}
</script>

<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 page-transition">
	<Masthead
		date={new Date(digest.metadata.generatedAt).toLocaleDateString('en-US', {
			weekday: 'long',
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		})}
		volume={1}
		issue={47}
	/>

	<!-- Action buttons -->
	<div class="flex items-center justify-between mb-8">
		<div class="flex items-center gap-4">
			<button onclick={refreshDigest} class="btn btn-primary" disabled={$loading.isLoading}>
				<RefreshCw class="w-4 h-4 {$loading.isLoading ? 'animate-spin' : ''}" />
				Generate New Digest
			</button>

			<!-- Mode indicator -->
			<a
				href="/settings"
				class="flex items-center gap-2 px-3 py-2 rounded-lg border border-paper-300 dark:border-ink-700 hover:border-blue-500 dark:hover:border-blue-500 transition-colors group"
				title="Change generation mode in settings"
			>
				<Settings class="w-4 h-4 text-ink-500 dark:text-paper-500 group-hover:text-blue-500" />
				<span class="text-sm text-ink-600 dark:text-paper-400 group-hover:text-blue-500">
					Mode:
					<span class="font-semibold {$preferences.generationMode === 'cloudflare' ? 'text-blue-600 dark:text-blue-400' : 'text-purple-600 dark:text-purple-400'}">
						{$preferences.generationMode === 'cloudflare' ? 'Cloudflare' : 'Server'}
					</span>
				</span>
			</a>

			<!-- Auth button -->
			{#if data.user}
				<form method="POST" action="/auth/logout" class="inline">
					<button
						type="submit"
						class="flex items-center gap-2 px-3 py-2 rounded-lg border border-paper-300 dark:border-ink-700 hover:border-red-500 dark:hover:border-red-500 transition-colors group"
						title="Logout from {data.user.email}"
					>
						<LogOut class="w-4 h-4 text-ink-500 dark:text-paper-500 group-hover:text-red-500" />
						<span class="text-sm text-ink-600 dark:text-paper-400 group-hover:text-red-500">
							Logout
						</span>
					</button>
				</form>
			{:else}
				<a
					href="/auth/login"
					class="flex items-center gap-2 px-3 py-2 rounded-lg border border-paper-300 dark:border-ink-700 hover:border-green-500 dark:hover:border-green-500 transition-colors group"
					title="Login to save preferences"
				>
					<LogIn class="w-4 h-4 text-ink-500 dark:text-paper-500 group-hover:text-green-500" />
					<span class="text-sm text-ink-600 dark:text-paper-400 group-hover:text-green-500">
						Login
					</span>
				</a>
			{/if}
		</div>

		<a href="/history" class="btn btn-secondary">
			<Calendar class="w-4 h-4" />
			View History
		</a>
	</div>

	<!-- Cross-story connections -->
	{#if digest.crossStoryConnections}
		<div class="mb-8 p-6 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
			<h2 class="text-lg font-serif font-bold text-purple-900 dark:text-purple-300 mb-2 flex items-center gap-2">
				<ChevronRight class="w-5 h-5" />
				Across the Stories
			</h2>
			<p class="text-ink-700 dark:text-paper-300">{digest.crossStoryConnections}</p>
		</div>
	{/if}

	<!-- Skeptic's summary -->
	{#if digest.skepticsSummary}
		<div class="mb-8 skeptics-corner">
			<div class="skeptics-corner-title">Editor's Skeptic Note</div>
			<p>{digest.skepticsSummary}</p>
		</div>
	{/if}

	<!-- Main content - bifold layout -->
	<BifoldLayout sections={digest.sections} />

	<!-- Stats footer -->
	<DigestStats metadata={digest.metadata} />
</main>
