<script lang="ts">
	import { preferences, user, loading, error, theme } from '$stores';
	import {
		ArrowLeft,
		Plus,
		Trash2,
		GripVertical,
		Mail,
		Rss,
		Globe,
		Save,
		RotateCcw,
		Moon,
		Sun,
		Cloud,
		Server,
		Zap,
		DollarSign,
		Wrench,
		Brain,
		Rocket
	} from 'lucide-svelte';
	import type { TopicPreference, StylePreferences } from '$types';

	// Local state for editing
	let topics = $state<TopicPreference[]>([...$preferences.topics]);
	let deliveryFrequency = $state($preferences.deliveryFrequency);
	let deliveryTime = $state($preferences.deliveryTime);
	let channels = $state<('web' | 'rss' | 'email')[]>([...$preferences.channels]);
	let style = $state<StylePreferences>({ ...$preferences.style });
	let generationMode = $state<'cloudflare' | 'server'>($preferences.generationMode || 'cloudflare');

	// New topic form
	let newTopicName = $state('');
	let newTopicKeywords = $state('');
	let showNewTopicForm = $state(false);

	// Track unsaved changes
	let hasChanges = $derived(
		JSON.stringify({
			topics,
			deliveryFrequency,
			deliveryTime,
			channels,
			style,
			generationMode
		}) !==
			JSON.stringify({
				topics: $preferences.topics,
				deliveryFrequency: $preferences.deliveryFrequency,
				deliveryTime: $preferences.deliveryTime,
				channels: $preferences.channels,
				style: $preferences.style,
				generationMode: $preferences.generationMode
			})
	);

	function addTopic() {
		if (!newTopicName.trim()) return;

		const keywords = newTopicKeywords
			.split(',')
			.map((k) => k.trim())
			.filter(Boolean);

		topics = [
			...topics,
			{
				name: newTopicName.trim(),
				keywords,
				priority: topics.length + 1,
				enabled: true
			}
		];

		newTopicName = '';
		newTopicKeywords = '';
		showNewTopicForm = false;
	}

	function removeTopic(index: number) {
		topics = topics.filter((_, i) => i !== index);
		// Reorder priorities
		topics = topics.map((t, i) => ({ ...t, priority: i + 1 }));
	}

	function toggleTopic(index: number) {
		topics = topics.map((t, i) => (i === index ? { ...t, enabled: !t.enabled } : t));
	}

	function moveTopic(index: number, direction: 'up' | 'down') {
		if (direction === 'up' && index === 0) return;
		if (direction === 'down' && index === topics.length - 1) return;

		const newTopics = [...topics];
		const targetIndex = direction === 'up' ? index - 1 : index + 1;
		[newTopics[index], newTopics[targetIndex]] = [newTopics[targetIndex], newTopics[index]];

		// Update priorities
		topics = newTopics.map((t, i) => ({ ...t, priority: i + 1 }));
	}

	function toggleChannel(channel: 'web' | 'rss' | 'email') {
		if (channels.includes(channel)) {
			channels = channels.filter((c) => c !== channel);
		} else {
			channels = [...channels, channel];
		}
	}

	async function saveSettings() {
		loading.start('Saving settings...');

		try {
			// Update store
			preferences.set({
				topics,
				deliveryFrequency,
				deliveryTime,
				channels,
				style,
				generationMode
			});

			// TODO: Save to API
			await new Promise((resolve) => setTimeout(resolve, 500));

			loading.stop();
		} catch (err) {
			error.set('Failed to save settings');
			loading.stop();
		}
	}

	function resetSettings() {
		preferences.reset();
		topics = [...$preferences.topics];
		deliveryFrequency = $preferences.deliveryFrequency;
		deliveryTime = $preferences.deliveryTime;
		channels = [...$preferences.channels];
		style = { ...$preferences.style };
		generationMode = $preferences.generationMode || 'cloudflare';
	}
</script>

<main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 page-transition">
	<!-- Header -->
	<header class="mb-8">
		<a href="/" class="inline-flex items-center gap-2 text-ink-600 dark:text-paper-400 hover:text-ink-900 dark:hover:text-paper-100 mb-4">
			<ArrowLeft class="w-4 h-4" />
			Back to Digest
		</a>
		<h1 class="text-4xl font-serif font-bold text-ink-900 dark:text-paper-100">Settings</h1>
		<p class="text-ink-600 dark:text-paper-400 mt-2">
			Customize your news digest preferences
		</p>
	</header>

	<!-- Appearance Section -->
	<section class="mb-12">
		<h2 class="text-2xl font-serif font-bold text-ink-900 dark:text-paper-100 mb-4">Appearance</h2>

		<div class="flex items-center justify-between p-4 bg-paper-50 dark:bg-ink-900 rounded-lg border border-paper-200 dark:border-ink-800">
			<div>
				<span class="font-medium text-ink-900 dark:text-paper-100 block mb-1">Dark Mode</span>
				<span class="text-sm text-ink-500 dark:text-paper-500">Use dark color scheme</span>
			</div>
			<button
				onclick={() => theme.toggle()}
				class="flex items-center gap-2 px-4 py-2 rounded-lg border-2 transition-all {$theme === 'dark'
					? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
					: 'border-paper-300 dark:border-ink-700'}"
				aria-label="Toggle dark mode"
			>
				{#if $theme === 'dark'}
					<Moon class="w-5 h-5 text-blue-500" />
					<span class="text-sm font-medium text-blue-500">Dark</span>
				{:else}
					<Sun class="w-5 h-5 text-ink-600" />
					<span class="text-sm font-medium text-ink-600">Light</span>
				{/if}
			</button>
		</div>
	</section>

	<!-- Generation Mode Section -->
	<section class="mb-12">
		<h2 class="text-2xl font-serif font-bold text-ink-900 dark:text-paper-100 mb-4">
			Generation Mode
		</h2>
		<p class="text-ink-600 dark:text-paper-400 mb-4">
			Choose how digests are generated
		</p>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
			<!-- Cloudflare Mode -->
			<button
				onclick={() => (generationMode = 'cloudflare')}
				class="p-6 rounded-lg border-2 transition-all text-left {generationMode === 'cloudflare'
					? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
					: 'border-paper-300 dark:border-ink-700 hover:border-blue-300 dark:hover:border-blue-700'}"
			>
				<div class="flex items-center gap-3 mb-3">
					<Cloud
						class="w-6 h-6 {generationMode === 'cloudflare' ? 'text-blue-500' : 'text-ink-600 dark:text-paper-400'}"
					/>
					<span
						class="text-lg font-semibold {generationMode === 'cloudflare' ? 'text-blue-500' : 'text-ink-900 dark:text-paper-100'}"
					>
						Cloudflare
					</span>
					{#if generationMode === 'cloudflare'}
						<span
							class="ml-auto px-2 py-1 text-xs font-medium bg-blue-500 text-white rounded"
						>
							Active
						</span>
					{/if}
				</div>
				<p class="text-sm text-ink-600 dark:text-paper-400">
					Fast, serverless generation using Durable Objects. Runs entirely on Cloudflare's edge
					network.
				</p>
				<div class="mt-3 flex items-center gap-3 text-xs text-ink-500 dark:text-paper-500">
					<span class="flex items-center gap-1">
						<Zap class="w-3 h-3" />
						Ultra-fast
					</span>
					<span>•</span>
					<span class="flex items-center gap-1">
						<DollarSign class="w-3 h-3" />
						Low cost
					</span>
					<span>•</span>
					<span class="flex items-center gap-1">
						<Globe class="w-3 h-3" />
						Global
					</span>
				</div>
			</button>

			<!-- Server Mode -->
			<button
				onclick={() => (generationMode = 'server')}
				class="p-6 rounded-lg border-2 transition-all text-left {generationMode === 'server'
					? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
					: 'border-paper-300 dark:border-ink-700 hover:border-purple-300 dark:hover:border-purple-700'}"
			>
				<div class="flex items-center gap-3 mb-3">
					<Server
						class="w-6 h-6 {generationMode === 'server' ? 'text-purple-500' : 'text-ink-600 dark:text-paper-400'}"
					/>
					<span
						class="text-lg font-semibold {generationMode === 'server' ? 'text-purple-500' : 'text-ink-900 dark:text-paper-100'}"
					>
						Dedicated Server
					</span>
					{#if generationMode === 'server'}
						<span
							class="ml-auto px-2 py-1 text-xs font-medium bg-purple-500 text-white rounded"
						>
							Active
						</span>
					{/if}
				</div>
				<p class="text-sm text-ink-600 dark:text-paper-400">
					On-demand ephemeral servers for complex processing. Provisions a Hetzner VPS for each
					digest.
				</p>
				<div class="mt-3 flex items-center gap-3 text-xs text-ink-500 dark:text-paper-500">
					<span class="flex items-center gap-1">
						<Wrench class="w-3 h-3" />
						Full control
					</span>
					<span>•</span>
					<span class="flex items-center gap-1">
						<Brain class="w-3 h-3" />
						Advanced processing
					</span>
					<span>•</span>
					<span class="flex items-center gap-1">
						<Rocket class="w-3 h-3" />
						Self-destructs
					</span>
				</div>
			</button>
		</div>
	</section>

	<!-- Topics Section -->
	<section class="mb-12">
		<div class="flex items-center justify-between mb-4">
			<h2 class="text-2xl font-serif font-bold text-ink-900 dark:text-paper-100">Topics</h2>
			<button onclick={() => (showNewTopicForm = !showNewTopicForm)} class="btn btn-secondary">
				<Plus class="w-4 h-4" />
				Add Topic
			</button>
		</div>

		<!-- New topic form -->
		{#if showNewTopicForm}
			<div class="mb-6 p-4 bg-paper-100 dark:bg-ink-900 rounded-lg border border-paper-300 dark:border-ink-700">
				<div class="space-y-4">
					<div>
						<label for="topicName" class="block text-sm font-medium text-ink-700 dark:text-paper-300 mb-1">
							Topic Name
						</label>
						<input
							id="topicName"
							type="text"
							bind:value={newTopicName}
							placeholder="e.g., Climate Science"
							class="w-full px-3 py-2 rounded-lg border border-paper-300 dark:border-ink-700 bg-white dark:bg-ink-800 text-ink-900 dark:text-paper-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						/>
					</div>
					<div>
						<label for="topicKeywords" class="block text-sm font-medium text-ink-700 dark:text-paper-300 mb-1">
							Keywords (comma-separated)
						</label>
						<input
							id="topicKeywords"
							type="text"
							bind:value={newTopicKeywords}
							placeholder="e.g., climate, environment, emissions"
							class="w-full px-3 py-2 rounded-lg border border-paper-300 dark:border-ink-700 bg-white dark:bg-ink-800 text-ink-900 dark:text-paper-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						/>
					</div>
					<div class="flex gap-2">
						<button onclick={addTopic} class="btn btn-primary">Add</button>
						<button onclick={() => (showNewTopicForm = false)} class="btn btn-ghost">Cancel</button>
					</div>
				</div>
			</div>
		{/if}

		<!-- Topic list -->
		<div class="space-y-2">
			{#each topics as topic, index}
				<div class="flex items-center gap-3 p-4 bg-paper-50 dark:bg-ink-900 rounded-lg border border-paper-200 dark:border-ink-800">
					<div class="flex flex-col gap-1">
						<button
							onclick={() => moveTopic(index, 'up')}
							disabled={index === 0}
							class="p-1 text-ink-400 hover:text-ink-600 dark:hover:text-paper-400 disabled:opacity-30"
							aria-label="Move up"
						>
							<GripVertical class="w-4 h-4" />
						</button>
					</div>

					<label class="flex items-center gap-3 flex-1 cursor-pointer">
						<input
							type="checkbox"
							checked={topic.enabled}
							onchange={() => toggleTopic(index)}
							class="w-5 h-5 rounded border-paper-300 dark:border-ink-600 text-blue-600 focus:ring-blue-500"
						/>
						<div class="flex-1">
							<span class="font-medium text-ink-900 dark:text-paper-100 {!topic.enabled ? 'opacity-50' : ''}">
								{topic.name}
							</span>
							<p class="text-sm text-ink-500 dark:text-paper-500 {!topic.enabled ? 'opacity-50' : ''}">
								{topic.keywords.join(', ')}
							</p>
						</div>
					</label>

					<span class="text-sm text-ink-400 dark:text-paper-600">#{topic.priority}</span>

					<button
						onclick={() => removeTopic(index)}
						class="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
						aria-label="Remove topic"
					>
						<Trash2 class="w-4 h-4" />
					</button>
				</div>
			{/each}
		</div>

		{#if topics.length === 0}
			<p class="text-ink-500 dark:text-paper-500 text-center py-8">
				No topics configured. Add one to get started.
			</p>
		{/if}
	</section>

	<!-- Delivery Settings -->
	<section class="mb-12">
		<h2 class="text-2xl font-serif font-bold text-ink-900 dark:text-paper-100 mb-4">Delivery</h2>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<div>
				<label for="frequency" class="block text-sm font-medium text-ink-700 dark:text-paper-300 mb-2">
					Frequency
				</label>
				<select
					id="frequency"
					bind:value={deliveryFrequency}
					class="w-full px-3 py-2 rounded-lg border border-paper-300 dark:border-ink-700 bg-white dark:bg-ink-800 text-ink-900 dark:text-paper-100 focus:ring-2 focus:ring-blue-500"
				>
					<option value="hourly">Hourly</option>
					<option value="daily">Daily</option>
					<option value="weekly">Weekly</option>
					<option value="biweekly">Bi-weekly</option>
					<option value="monthly">Monthly</option>
				</select>
			</div>

			<div>
				<label for="time" class="block text-sm font-medium text-ink-700 dark:text-paper-300 mb-2">
					Preferred Time
				</label>
				<input
					id="time"
					type="time"
					bind:value={deliveryTime}
					class="w-full px-3 py-2 rounded-lg border border-paper-300 dark:border-ink-700 bg-white dark:bg-ink-800 text-ink-900 dark:text-paper-100 focus:ring-2 focus:ring-blue-500"
				/>
			</div>
		</div>
	</section>

	<!-- Channels -->
	<section class="mb-12">
		<h2 class="text-2xl font-serif font-bold text-ink-900 dark:text-paper-100 mb-4">Channels</h2>
		<p class="text-ink-600 dark:text-paper-400 mb-4">
			Choose how you want to receive your digest
		</p>

		<div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
			<button
				onclick={() => toggleChannel('web')}
				class="flex items-center gap-3 p-4 rounded-lg border-2 transition-all {channels.includes('web')
					? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
					: 'border-paper-300 dark:border-ink-700 hover:border-paper-400 dark:hover:border-ink-600'}"
			>
				<Globe class="w-6 h-6 {channels.includes('web') ? 'text-blue-500' : 'text-ink-400 dark:text-paper-600'}" />
				<div class="text-left">
					<span class="block font-medium text-ink-900 dark:text-paper-100">Web</span>
					<span class="text-sm text-ink-500 dark:text-paper-500">View in browser</span>
				</div>
			</button>

			<button
				onclick={() => toggleChannel('email')}
				class="flex items-center gap-3 p-4 rounded-lg border-2 transition-all {channels.includes('email')
					? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
					: 'border-paper-300 dark:border-ink-700 hover:border-paper-400 dark:hover:border-ink-600'}"
			>
				<Mail class="w-6 h-6 {channels.includes('email') ? 'text-blue-500' : 'text-ink-400 dark:text-paper-600'}" />
				<div class="text-left">
					<span class="block font-medium text-ink-900 dark:text-paper-100">Email</span>
					<span class="text-sm text-ink-500 dark:text-paper-500">Delivered to inbox</span>
				</div>
			</button>

			<button
				onclick={() => toggleChannel('rss')}
				class="flex items-center gap-3 p-4 rounded-lg border-2 transition-all {channels.includes('rss')
					? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
					: 'border-paper-300 dark:border-ink-700 hover:border-paper-400 dark:hover:border-ink-600'}"
			>
				<Rss class="w-6 h-6 {channels.includes('rss') ? 'text-blue-500' : 'text-ink-400 dark:text-paper-600'}" />
				<div class="text-left">
					<span class="block font-medium text-ink-900 dark:text-paper-100">RSS</span>
					<span class="text-sm text-ink-500 dark:text-paper-500">Subscribe via feed</span>
				</div>
			</button>
		</div>
	</section>

	<!-- Style Preferences -->
	<section class="mb-12">
		<h2 class="text-2xl font-serif font-bold text-ink-900 dark:text-paper-100 mb-4">Reading Style</h2>

		<div class="space-y-6">
			<!-- Tone -->
			<div>
				<label for="tone" class="block text-sm font-medium text-ink-700 dark:text-paper-300 mb-2">
					Tone
				</label>
				<select
					id="tone"
					bind:value={style.tone}
					class="w-full px-3 py-2 rounded-lg border border-paper-300 dark:border-ink-700 bg-white dark:bg-ink-800 text-ink-900 dark:text-paper-100 focus:ring-2 focus:ring-blue-500"
				>
					<option value="hn-style">Hacker News Style</option>
					<option value="formal">Formal / Academic</option>
					<option value="casual">Casual / Conversational</option>
				</select>
			</div>

			<!-- Skepticism Level -->
			<div>
				<label class="block text-sm font-medium text-ink-700 dark:text-paper-300 mb-2">
					Skepticism Level
				</label>
				<div class="flex items-center gap-4">
					<input
						type="range"
						min="1"
						max="5"
						bind:value={style.skepticismLevel}
						class="flex-1 h-2 rounded-lg appearance-none bg-paper-300 dark:bg-ink-700"
					/>
					<span class="w-8 text-center font-mono text-ink-900 dark:text-paper-100">{style.skepticismLevel}</span>
				</div>
				<p class="text-sm text-ink-500 dark:text-paper-500 mt-1">
					{#if style.skepticismLevel === 1}
						Minimal skepticism - mostly positive coverage
					{:else if style.skepticismLevel === 2}
						Light skepticism - occasional caveats
					{:else if style.skepticismLevel === 3}
						Balanced - fair critique with praise
					{:else if style.skepticismLevel === 4}
						Critical - detailed questioning
					{:else}
						Maximum skepticism - thorough scrutiny
					{/if}
				</p>
			</div>

			<!-- Technical Depth -->
			<div>
				<label class="block text-sm font-medium text-ink-700 dark:text-paper-300 mb-2">
					Technical Depth
				</label>
				<div class="flex items-center gap-4">
					<input
						type="range"
						min="1"
						max="5"
						bind:value={style.technicalDepth}
						class="flex-1 h-2 rounded-lg appearance-none bg-paper-300 dark:bg-ink-700"
					/>
					<span class="w-8 text-center font-mono text-ink-900 dark:text-paper-100">{style.technicalDepth}</span>
				</div>
				<p class="text-sm text-ink-500 dark:text-paper-500 mt-1">
					{#if style.technicalDepth === 1}
						Beginner - plain language explanations
					{:else if style.technicalDepth === 2}
						Intermediate - some technical terms
					{:else if style.technicalDepth === 3}
						Balanced - accessible but detailed
					{:else if style.technicalDepth === 4}
						Advanced - technical deep-dives
					{:else}
						Expert - full technical detail
					{/if}
				</p>
			</div>

			<!-- Toggles -->
			<div class="space-y-4">
				<label class="flex items-center gap-3 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={style.includeBiasAnalysis}
						class="w-5 h-5 rounded border-paper-300 dark:border-ink-600 text-blue-600 focus:ring-blue-500"
					/>
					<div>
						<span class="font-medium text-ink-900 dark:text-paper-100">Include Bias Analysis</span>
						<p class="text-sm text-ink-500 dark:text-paper-500">Show political/ideological lean indicators</p>
					</div>
				</label>

				<label class="flex items-center gap-3 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={style.includeCrossConnections}
						class="w-5 h-5 rounded border-paper-300 dark:border-ink-600 text-blue-600 focus:ring-blue-500"
					/>
					<div>
						<span class="font-medium text-ink-900 dark:text-paper-100">Include Cross-Story Connections</span>
						<p class="text-sm text-ink-500 dark:text-paper-500">Highlight themes across different articles</p>
					</div>
				</label>
			</div>
		</div>
	</section>

	<!-- Action buttons -->
	<footer class="flex items-center justify-between pt-8 border-t border-paper-300 dark:border-ink-700">
		<button onclick={resetSettings} class="btn btn-ghost">
			<RotateCcw class="w-4 h-4" />
			Reset to Defaults
		</button>

		<div class="flex items-center gap-4">
			{#if hasChanges}
				<span class="text-sm text-amber-600 dark:text-amber-400">Unsaved changes</span>
			{/if}
			<button onclick={saveSettings} class="btn btn-primary" disabled={!hasChanges || $loading.isLoading}>
				<Save class="w-4 h-4" />
				Save Settings
			</button>
		</div>
	</footer>
</main>
