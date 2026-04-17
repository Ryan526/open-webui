<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, onDestroy, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import dayjs from 'dayjs';

	import { getQCTestRunById } from '$lib/apis/qc';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let runId: string;

	let run: any = null;
	let loading = true;
	let poll: number | null = null;
	let destroyed = false;

	const load = async () => {
		try {
			const res = await getQCTestRunById(localStorage.token, runId);
			if (destroyed) return;
			run = res;
			loading = false;
			if (res?.status === 'running' && !poll) {
				poll = setInterval(load, 5000) as unknown as number;
			} else if (poll && res?.status !== 'running') {
				clearInterval(poll);
				poll = null;
			}
		} catch (e) {
			toast.error(`${e}`);
			loading = false;
		}
	};

	onMount(load);
	onDestroy(() => {
		destroyed = true;
		if (poll) clearInterval(poll);
	});
</script>

{#if loading}
	<div class="flex justify-center py-12"><Spinner className="size-5" /></div>
{:else if run}
	<div class="py-3">
		<button
			class="text-sm text-gray-500 hover:text-gray-700 transition mb-4"
			on:click={() => goto('/qc/test-runs')}
		>
			← {$i18n.t('Back to Test Runs')}
		</button>

		<div class="flex items-center gap-3 mb-4">
			<h2 class="text-lg font-medium">{$i18n.t('Test Run')}</h2>
			<span class="capitalize text-[10px] px-1.5 py-0.5 rounded {run.status === 'completed' ? 'bg-green-500/15 text-green-700' : run.status === 'running' ? 'bg-blue-500/15 text-blue-700' : run.status === 'failed' ? 'bg-red-500/15 text-red-700' : 'bg-gray-500/15 text-gray-700'}">
				{run.status}
			</span>
			<span class="text-xs text-gray-500">{dayjs(run.created_at * 1000).fromNow()}</span>
		</div>

		<div class="grid grid-cols-2 gap-3 mb-6">
			<div class="p-3 rounded-xl border border-gray-200 dark:border-gray-800">
				<div class="text-[11px] text-gray-500">{$i18n.t('Test Set')}</div>
				<div class="text-sm">{run.test_set?.name || run.test_set_id}</div>
			</div>
			<div class="p-3 rounded-xl border border-gray-200 dark:border-gray-800">
				<div class="text-[11px] text-gray-500">{$i18n.t('Template')}</div>
				<div class="text-sm">{run.template_id || '—'}</div>
				{#if run.template_version_id}
					<div class="text-[10px] text-gray-400">version: {run.template_version_id.slice(0, 8)}...</div>
				{/if}
			</div>
		</div>

		{#if run.metrics}
			<div class="mb-6">
				<h3 class="text-sm font-medium mb-2">{$i18n.t('Metrics')}</h3>
				<div class="grid grid-cols-3 gap-3">
					<div class="p-3 rounded-xl border border-gray-200 dark:border-gray-800">
						<div class="text-[11px] text-gray-500">{$i18n.t('Precision')}</div>
						<div class="text-lg font-mono">{run.metrics.precision}</div>
					</div>
					<div class="p-3 rounded-xl border border-gray-200 dark:border-gray-800">
						<div class="text-[11px] text-gray-500">{$i18n.t('Recall')}</div>
						<div class="text-lg font-mono">{run.metrics.recall}</div>
					</div>
					<div class="p-3 rounded-xl border border-gray-200 dark:border-gray-800">
						<div class="text-[11px] text-gray-500">F1</div>
						<div class="text-lg font-mono">{run.metrics.f1}</div>
					</div>
				</div>
				<div class="mt-3 text-xs text-gray-600 dark:text-gray-400">
					TP: {run.metrics.tp} · FP: {run.metrics.fp} · FN: {run.metrics.fn}
				</div>
				{#if run.metrics.per_severity}
					<div class="mt-3">
						<h4 class="text-xs font-medium mb-1">{$i18n.t('Per severity')}</h4>
						<div class="grid grid-cols-4 gap-2 text-xs">
							{#each ['critical', 'major', 'minor', 'info'] as sev}
								{@const cell = run.metrics.per_severity[sev]}
								<div class="p-2 rounded-lg border border-gray-200 dark:border-gray-800">
									<div class="text-[10px] text-gray-500 capitalize">{sev}</div>
									<div class="font-mono">tp {cell?.tp ?? 0} · fp {cell?.fp ?? 0} · fn {cell?.fn ?? 0}</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		{:else}
			<div class="text-sm text-gray-500 py-4">{$i18n.t('Metrics will appear when the run completes.')}</div>
		{/if}

		{#if run.shadow_job_id}
			<div class="text-xs">
				<a class="text-blue-600 hover:underline" href="/qc/jobs/{run.shadow_job_id}">
					{$i18n.t('View shadow job →')}
				</a>
			</div>
		{/if}
	</div>
{/if}
