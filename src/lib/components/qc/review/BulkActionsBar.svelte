<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, createEventDispatcher } from 'svelte';

	import { bulkUpdateFindings } from '$lib/apis/qc';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let jobId: string;
	export let selectedIds: Set<string>;

	let working = false;
	let severityValue = 'minor';
	let showSeverityPicker = false;

	$: count = selectedIds.size;

	const run = async (action: string, extras: Record<string, unknown> = {}) => {
		if (count === 0) return;
		working = true;
		try {
			await bulkUpdateFindings(localStorage.token, jobId, {
				finding_ids: Array.from(selectedIds),
				action: action as any,
				...extras
			});
			toast.success($i18n.t('{{count}} finding(s) updated', { count }));
			dispatch('done');
		} catch (e) {
			toast.error(`${e}`);
		}
		working = false;
	};

	const handleDelete = async () => {
		if (!confirm($i18n.t('Delete {{count}} finding(s)?', { count }))) return;
		await run('delete');
	};
</script>

{#if count > 0}
	<div
		class="flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/30 border-b border-blue-200 dark:border-blue-800 text-xs"
	>
		<span class="font-medium text-blue-700 dark:text-blue-300">
			{count} {$i18n.t('selected')}
		</span>
		<div class="flex-1"></div>
		<button
			class="px-2 py-0.5 rounded border border-gray-200 dark:border-gray-700 hover:bg-white dark:hover:bg-gray-800 disabled:opacity-50"
			disabled={working}
			on:click={() => run('confirm')}
		>
			{$i18n.t('Confirm')}
		</button>
		<button
			class="px-2 py-0.5 rounded border border-gray-200 dark:border-gray-700 hover:bg-white dark:hover:bg-gray-800 disabled:opacity-50"
			disabled={working}
			on:click={() => run('dismiss')}
		>
			{$i18n.t('Dismiss')}
		</button>
		<div class="relative">
			<button
				class="px-2 py-0.5 rounded border border-gray-200 dark:border-gray-700 hover:bg-white dark:hover:bg-gray-800 disabled:opacity-50"
				disabled={working}
				on:click={() => (showSeverityPicker = !showSeverityPicker)}
			>
				{$i18n.t('Severity')} ▾
			</button>
			{#if showSeverityPicker}
				<div
					class="absolute right-0 top-full mt-1 w-32 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-20 p-1 flex flex-col"
				>
					{#each ['critical', 'major', 'minor', 'info'] as sev}
						<button
							class="px-2 py-1 text-left text-xs hover:bg-gray-100 dark:hover:bg-gray-800 rounded capitalize"
							on:click={() => {
								showSeverityPicker = false;
								run('severity', { severity: sev });
							}}
						>
							{sev}
						</button>
					{/each}
				</div>
			{/if}
		</div>
		<button
			class="px-2 py-0.5 rounded border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 disabled:opacity-50"
			disabled={working}
			on:click={handleDelete}
		>
			{$i18n.t('Delete')}
		</button>
		<button
			class="px-2 py-0.5 rounded border border-gray-200 dark:border-gray-700 hover:bg-white dark:hover:bg-gray-800 text-gray-600"
			on:click={() => dispatch('clear')}
		>
			{$i18n.t('Clear')}
		</button>
	</div>
{/if}
