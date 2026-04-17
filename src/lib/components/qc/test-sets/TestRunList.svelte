<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import dayjs from 'dayjs';

	import { getQCTestRuns } from '$lib/apis/qc';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let runs: any[] = [];
	let loading = true;

	const load = async () => {
		loading = true;
		try {
			runs = (await getQCTestRuns(localStorage.token)) || [];
		} catch (e) {
			toast.error(`${e}`);
		}
		loading = false;
	};

	onMount(load);
</script>

<div class="mt-1 mb-3 flex items-center justify-between">
	<h2 class="text-sm font-medium">{$i18n.t('Test Runs')}</h2>
	<button class="text-xs text-blue-600 hover:underline" on:click={load}>{$i18n.t('Reload')}</button>
</div>

{#if loading}
	<div class="flex justify-center py-12"><Spinner className="size-5" /></div>
{:else if runs.length === 0}
	<div class="text-center text-gray-500 py-12 text-sm">{$i18n.t('No test runs yet.')}</div>
{:else}
	<div class="space-y-2">
		{#each runs as r}
			<a
				href="/qc/test-runs/{r.id}"
				class="block p-3 rounded-xl border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
			>
				<div class="flex items-center gap-2 text-xs">
					<span class="capitalize text-[10px] px-1.5 py-0.5 rounded {r.status === 'completed' ? 'bg-green-500/15 text-green-700' : r.status === 'running' ? 'bg-blue-500/15 text-blue-700' : r.status === 'failed' ? 'bg-red-500/15 text-red-700' : 'bg-gray-500/15 text-gray-700'}">
						{r.status}
					</span>
					<span class="font-medium">{r.test_set_id.slice(0, 8)}...</span>
					{#if r.metrics}
						<span class="text-gray-500">p={r.metrics.precision}, r={r.metrics.recall}, f1={r.metrics.f1}</span>
					{/if}
					<span class="ml-auto text-gray-400">{dayjs(r.created_at * 1000).fromNow()}</span>
				</div>
			</a>
		{/each}
	</div>
{/if}
