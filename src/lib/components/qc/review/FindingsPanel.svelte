<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, createEventDispatcher } from 'svelte';

	import { updateQCFinding, deleteQCFinding, createQCFinding } from '$lib/apis/qc';
	import SeverityBadge from '../SeverityBadge.svelte';
	import FindingCard from './FindingCard.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let findings: any[];
	export let jobId: string;
	export let selectedDoc: any;
	export let selectedPage: number;

	let severityFilter = '';
	let statusFilter = '';
	let showAddFinding = false;

	// New finding form
	let newTitle = '';
	let newDescription = '';
	let newSeverity = 'minor';

	$: filteredFindings = findings.filter((f) => {
		if (severityFilter && f.severity !== severityFilter) return false;
		if (statusFilter && f.status !== statusFilter) return false;
		return true;
	});

	$: sortedFindings = [...filteredFindings].sort((a, b) => a.finding_number - b.finding_number);

	const handleStatusChange = async (findingId: string, newStatus: string) => {
		try {
			await updateQCFinding(localStorage.token, jobId, findingId, { status: newStatus });
			dispatch('refresh');
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const handleDelete = async (findingId: string) => {
		try {
			await deleteQCFinding(localStorage.token, jobId, findingId);
			dispatch('refresh');
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const handleAddFinding = async () => {
		if (!newTitle.trim()) return;
		try {
			await createQCFinding(localStorage.token, jobId, {
				document_id: selectedDoc?.id,
				source: 'human',
				page_number: selectedPage,
				severity: newSeverity,
				title: newTitle.trim(),
				description: newDescription.trim()
			});
			toast.success($i18n.t('Finding added'));
			newTitle = '';
			newDescription = '';
			showAddFinding = false;
			dispatch('refresh');
		} catch (e) {
			toast.error(`${e}`);
		}
	};
</script>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="px-3 py-2 border-b border-gray-200 dark:border-gray-800">
		<div class="flex items-center justify-between mb-2">
			<h3 class="text-sm font-medium">{$i18n.t('Findings')} ({filteredFindings.length})</h3>
			<button
				class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition"
				on:click={() => (showAddFinding = !showAddFinding)}
				title={$i18n.t('Add Manual Finding')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="size-4"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
				</svg>
			</button>
		</div>

		<div class="flex gap-1">
			<select
				bind:value={severityFilter}
				class="flex-1 text-xs rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1 outline-none"
			>
				<option value="">{$i18n.t('All Severity')}</option>
				<option value="critical">{$i18n.t('Critical')}</option>
				<option value="major">{$i18n.t('Major')}</option>
				<option value="minor">{$i18n.t('Minor')}</option>
				<option value="info">{$i18n.t('Info')}</option>
			</select>
			<select
				bind:value={statusFilter}
				class="flex-1 text-xs rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1 outline-none"
			>
				<option value="">{$i18n.t('All Status')}</option>
				<option value="open">{$i18n.t('Open')}</option>
				<option value="confirmed">{$i18n.t('Confirmed')}</option>
				<option value="dismissed">{$i18n.t('Dismissed')}</option>
				<option value="resolved">{$i18n.t('Resolved')}</option>
			</select>
		</div>
	</div>

	<!-- Add Finding Form -->
	{#if showAddFinding}
		<div class="px-3 py-2 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-850">
			<input
				type="text"
				bind:value={newTitle}
				placeholder={$i18n.t('Finding title...')}
				class="w-full text-xs rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none mb-1"
			/>
			<textarea
				bind:value={newDescription}
				placeholder={$i18n.t('Description...')}
				rows="2"
				class="w-full text-xs rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none mb-1"
			></textarea>
			<div class="flex items-center gap-2">
				<select
					bind:value={newSeverity}
					class="text-xs rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1 outline-none"
				>
					<option value="critical">Critical</option>
					<option value="major">Major</option>
					<option value="minor">Minor</option>
					<option value="info">Info</option>
				</select>
				<span class="text-xs text-gray-400">Page {selectedPage}</span>
				<div class="flex-1"></div>
				<button
					class="px-2 py-1 text-xs bg-black text-white dark:bg-white dark:text-black rounded-lg hover:opacity-90 transition"
					on:click={handleAddFinding}
				>
					{$i18n.t('Add')}
				</button>
			</div>
		</div>
	{/if}

	<!-- Findings list -->
	<div class="flex-1 overflow-y-auto">
		{#if sortedFindings.length === 0}
			<div class="text-center text-gray-400 py-8 text-xs">
				{$i18n.t('No findings')}
			</div>
		{:else}
			<div class="divide-y divide-gray-100 dark:divide-gray-850">
				{#each sortedFindings as finding}
					<FindingCard
						{finding}
						on:navigate={() => dispatch('navigate', finding)}
						on:statusChange={(e) => handleStatusChange(finding.id, e.detail)}
						on:delete={() => handleDelete(finding.id)}
					/>
				{/each}
			</div>
		{/if}
	</div>
</div>
