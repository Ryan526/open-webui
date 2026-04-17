<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, createEventDispatcher } from 'svelte';

	import {
		getJobDuplicates,
		recomputeDuplicates,
		bulkUpdateFindings
	} from '$lib/apis/qc';
	import SeverityBadge from '../SeverityBadge.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let jobId: string;
	export let show: boolean;

	let loading = true;
	let busy = false;
	let clusters: any[] = [];

	const load = async () => {
		loading = true;
		try {
			const res = await getJobDuplicates(localStorage.token, jobId);
			clusters = res?.clusters || [];
		} catch (e) {
			toast.error(`${e}`);
		}
		loading = false;
	};

	const recompute = async () => {
		busy = true;
		try {
			const r = await recomputeDuplicates(localStorage.token, jobId);
			toast.success(
				$i18n.t('{{n}} duplicate link(s) rebuilt', { n: r?.duplicates_linked ?? 0 })
			);
			await load();
			dispatch('change');
		} catch (e) {
			toast.error(`${e}`);
		}
		busy = false;
	};

	const unlinkOne = async (findingId: string) => {
		busy = true;
		try {
			await bulkUpdateFindings(localStorage.token, jobId, {
				finding_ids: [findingId],
				action: 'unlink_duplicate'
			});
			await load();
			dispatch('change');
		} catch (e) {
			toast.error(`${e}`);
		}
		busy = false;
	};

	const mergeIntoCanonical = async (canonicalId: string, dupId: string) => {
		busy = true;
		try {
			await bulkUpdateFindings(localStorage.token, jobId, {
				finding_ids: [dupId],
				action: 'merge_duplicate',
				canonical_finding_id: canonicalId
			});
			await load();
			dispatch('change');
		} catch (e) {
			toast.error(`${e}`);
		}
		busy = false;
	};

	$: if (show) load();
</script>

{#if show}
	<div
		class="fixed inset-0 z-40 flex items-center justify-center bg-black/50"
		on:click={() => (show = false)}
		on:keydown={(e) => {
			if (e.key === 'Escape') show = false;
		}}
		role="presentation"
	>
		<div
			class="w-[min(720px,calc(100vw-2rem))] max-h-[80vh] overflow-hidden bg-white dark:bg-gray-900 rounded-2xl shadow-xl flex flex-col"
			on:click|stopPropagation
			role="dialog"
		>
			<div class="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
				<h3 class="text-sm font-medium">{$i18n.t('Duplicate Clusters')}</h3>
				<div class="flex items-center gap-2">
					<button
						class="px-2 py-1 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50"
						on:click={recompute}
						disabled={busy}
					>
						{busy ? $i18n.t('Recomputing...') : $i18n.t('Recompute')}
					</button>
					<button
						class="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
						on:click={() => (show = false)}
					>
						✕
					</button>
				</div>
			</div>

			<div class="flex-1 overflow-y-auto p-3 space-y-3">
				{#if loading}
					<div class="flex justify-center py-8"><Spinner className="size-5" /></div>
				{:else if clusters.length === 0}
					<div class="text-center text-gray-500 py-8 text-sm">
						{$i18n.t('No duplicate clusters.')}
					</div>
				{:else}
					{#each clusters as c}
						<div class="rounded-xl border border-gray-200 dark:border-gray-800 p-3">
							<div class="flex items-center gap-2 mb-2">
								<span class="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-700 dark:text-amber-400 font-medium">
									CANONICAL
								</span>
								<SeverityBadge severity={c.canonical.severity} />
								<span class="text-sm font-medium truncate">#{c.canonical.finding_number} {c.canonical.title}</span>
							</div>
							<div class="text-xs text-gray-500 mb-2">
								p.{c.canonical.page_number ?? '?'} · {c.duplicates.length} {$i18n.t('duplicate(s)')}
							</div>
							<div class="space-y-1.5">
								{#each c.duplicates as d}
									<div class="flex items-center gap-2 text-xs p-2 rounded-lg bg-gray-50 dark:bg-gray-850">
										<SeverityBadge severity={d.severity} />
										<span class="truncate flex-1">#{d.finding_number} {d.title}</span>
										<span class="text-gray-400">p.{d.page_number ?? '?'}</span>
										<button
											class="px-2 py-0.5 rounded border border-gray-200 dark:border-gray-700 hover:bg-white dark:hover:bg-gray-800"
											on:click={() => unlinkOne(d.id)}
											disabled={busy}
										>
											{$i18n.t('Unlink')}
										</button>
									</div>
								{/each}
							</div>
						</div>
					{/each}
				{/if}
			</div>
		</div>
	</div>
{/if}
