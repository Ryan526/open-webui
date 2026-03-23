<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import SeverityBadge from '../SeverityBadge.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let finding: any;

	let expanded = false;
	let showDismissalInput = false;
	let dismissalReason = '';

	const statusOptions = [
		{ value: 'open', label: 'Open' },
		{ value: 'confirmed', label: 'Confirmed' },
		{ value: 'dismissed', label: 'Dismissed' },
		{ value: 'resolved', label: 'Resolved' }
	];

	const handleStatusChange = (newStatus: string) => {
		if (newStatus === 'dismissed') {
			showDismissalInput = true;
			dismissalReason = finding.meta?.dismissal_reason || '';
		} else {
			showDismissalInput = false;
			dispatch('statusChange', { status: newStatus });
		}
	};

	const saveDismissal = () => {
		dispatch('statusChange', { status: 'dismissed', dismissalReason: dismissalReason.trim() });
		showDismissalInput = false;
	};
</script>

<div class="px-3 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-850/50 transition">
	<!-- Header row -->
	<div class="flex items-start gap-2">
		<!-- Finding number badge -->
		{#if finding.source === 'cross_reference'}
			<!-- Cross-reference link icon -->
			<button
				class="shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold bg-purple-500 text-white"
				on:click={() => dispatch('navigate')}
				title={$i18n.t('Cross-reference finding')}
			>
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="size-3.5">
					<path stroke-linecap="round" stroke-linejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" />
				</svg>
			</button>
		{:else}
			<button
				class="shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold {finding.severity ===
				'critical'
					? 'bg-red-500 text-white'
					: finding.severity === 'major'
						? 'bg-orange-500 text-white'
						: finding.severity === 'minor'
							? 'bg-yellow-500 text-white'
							: 'bg-blue-500 text-white'}"
				on:click={() => dispatch('navigate')}
				title={$i18n.t('Go to page')}
			>
				{finding.finding_number || '?'}
			</button>
		{/if}

		<div class="flex-1 min-w-0">
			<div class="flex items-center gap-1.5 flex-wrap">
				<span class="text-xs font-medium truncate">{finding.title}</span>
				<SeverityBadge severity={finding.severity} />
				{#if finding.source === 'cross_reference'}
					<span class="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-600 dark:text-purple-400 font-medium">
						X-REF
					</span>
				{/if}
			</div>

			<div class="flex items-center gap-2 mt-0.5 text-xs text-gray-400">
				{#if finding.page_number}
					<button
						class="hover:text-blue-500 transition"
						on:click={() => dispatch('navigate')}
					>
						p.{finding.page_number}
					</button>
				{/if}
				<span class="capitalize">{finding.source === 'cross_reference' ? 'cross-ref' : finding.source}</span>
			</div>
		</div>

		<!-- Status dropdown -->
		<select
			class="text-xs rounded border border-gray-200 dark:border-gray-700 bg-transparent px-1 py-0.5 outline-none shrink-0 {finding.status ===
			'resolved'
				? 'text-green-600'
				: finding.status === 'dismissed'
					? 'text-gray-400'
					: finding.status === 'confirmed'
						? 'text-orange-600'
						: ''}"
			value={finding.status}
			on:change={(e) => handleStatusChange(e.target.value)}
		>
			{#each statusOptions as opt}
				<option value={opt.value}>{opt.label}</option>
			{/each}
		</select>
	</div>

	<!-- Dismissal reason input -->
	{#if showDismissalInput}
		<div class="mt-1.5 flex items-center gap-1.5">
			<input
				type="text"
				bind:value={dismissalReason}
				placeholder={$i18n.t('Why is this a false positive?')}
				class="flex-1 text-xs rounded border border-gray-200 dark:border-gray-700 bg-transparent px-2 py-1 outline-none"
				on:keydown={(e) => e.key === 'Enter' && saveDismissal()}
			/>
			<button
				class="px-2 py-1 text-xs bg-black text-white dark:bg-white dark:text-black rounded hover:opacity-90 transition shrink-0"
				on:click={saveDismissal}
			>
				{$i18n.t('Save')}
			</button>
		</div>
	{:else if finding.status === 'dismissed' && finding.meta?.dismissal_reason}
		<div class="mt-1 text-xs text-gray-400 italic truncate" title={finding.meta.dismissal_reason}>
			{$i18n.t('Reason')}: {finding.meta.dismissal_reason}
		</div>
	{/if}

	<!-- Expandable details -->
	{#if finding.description || finding.ai_response?.reasoning}
		<button
			class="text-xs text-gray-400 hover:text-gray-600 mt-1 flex items-center gap-1"
			on:click={() => (expanded = !expanded)}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="2"
				stroke="currentColor"
				class="size-3 transition-transform {expanded ? 'rotate-90' : ''}"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
			</svg>
			{expanded ? $i18n.t('Less') : $i18n.t('More')}
		</button>
	{/if}

	{#if expanded}
		<div class="mt-2 text-xs text-gray-600 dark:text-gray-400 space-y-1.5">
			{#if finding.description}
				<p>{finding.description}</p>
			{/if}
			{#if finding.ai_response?.reasoning}
				<div class="p-2 rounded-lg bg-gray-100 dark:bg-gray-800">
					<span class="font-medium">{$i18n.t('AI Reasoning')}:</span>
					{finding.ai_response.reasoning}
				</div>
			{/if}
			{#if finding.meta?.references?.length > 0}
				<div class="p-2 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800">
					<span class="font-medium text-purple-700 dark:text-purple-300">{$i18n.t('Referenced pages')}:</span>
					<div class="mt-1 space-y-0.5">
						{#each finding.meta.references as ref}
							<button
								class="block w-full text-left hover:text-purple-600 dark:hover:text-purple-400 transition px-1 py-0.5 rounded hover:bg-purple-100 dark:hover:bg-purple-900/30"
								on:click={() => dispatch('navigateRef', ref)}
							>
								<span class="font-medium">p.{ref.page_number}</span>
								{#if ref.reference_text}
									<span class="text-gray-500"> — {ref.reference_text}</span>
								{/if}
								{#if ref.context}
									<span class="text-gray-400 italic"> ({ref.context})</span>
								{/if}
							</button>
						{/each}
					</div>
				</div>
			{/if}
			<div class="flex items-center gap-2 pt-1">
				<button
					class="text-red-500 hover:text-red-700 transition text-xs"
					on:click={() => dispatch('delete')}
				>
					{$i18n.t('Delete')}
				</button>
			</div>
		</div>
	{/if}
</div>
