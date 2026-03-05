<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';

	import { getQCJobs, deleteQCJob } from '$lib/apis/qc';
	import JobStatusBadge from './JobStatusBadge.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	dayjs.extend(relativeTime);

	const i18n = getContext('i18n');

	let jobs: any[] = [];
	let loading = true;
	let statusFilter = '';

	const loadJobs = async () => {
		loading = true;
		try {
			jobs = (await getQCJobs(localStorage.token, statusFilter || undefined)) || [];
		} catch (e) {
			toast.error(`${e}`);
		}
		loading = false;
	};

	const handleDelete = async (id: string) => {
		if (!confirm('Are you sure you want to delete this job?')) return;
		try {
			await deleteQCJob(localStorage.token, id);
			toast.success($i18n.t('Job deleted'));
			await loadJobs();
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	$: if (statusFilter !== undefined) {
		loadJobs();
	}

	onMount(loadJobs);
</script>

<div class="mt-1 mb-3 flex justify-between items-center gap-2">
	<div class="flex items-center gap-2">
		<select
			bind:value={statusFilter}
			class="text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-1.5 outline-none"
		>
			<option value="">{$i18n.t('All Status')}</option>
			<option value="pending">{$i18n.t('Pending')}</option>
			<option value="running">{$i18n.t('Running')}</option>
			<option value="completed">{$i18n.t('Completed')}</option>
			<option value="failed">{$i18n.t('Failed')}</option>
		</select>
	</div>
	<button
		class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-xl"
		on:click={() => goto('/qc/jobs/create')}
	>
		+ {$i18n.t('New Job')}
	</button>
</div>

{#if loading}
	<div class="flex justify-center py-12">
		<Spinner className="size-5" />
	</div>
{:else if jobs.length === 0}
	<div class="text-center text-gray-500 dark:text-gray-400 py-12">
		{$i18n.t('No QC jobs found. Create one to start analyzing documents.')}
	</div>
{:else}
	<div class="space-y-2">
		{#each jobs as job}
			<a
				href="/qc/jobs/{job.id}"
				class="block p-4 rounded-xl border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
				draggable="false"
			>
				<div class="flex justify-between items-start">
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2">
							<h3 class="font-medium text-sm truncate">{job.name}</h3>
							<JobStatusBadge status={job.status} result={job.overall_result} />
						</div>
						{#if job.model_id}
							<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
								{$i18n.t('Model')}: {job.model_id}
							</p>
						{/if}
						{#if job.meta?.statistics}
							<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
								{job.meta.statistics.pages_analyzed || 0} pages, {job.meta.statistics.findings_count ||
									0} findings
							</p>
						{/if}
					</div>
					<div class="flex items-center gap-2 shrink-0">
						<span class="text-xs text-gray-400">{dayjs(job.updated_at * 1000).fromNow()}</span>
						<button
							class="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 transition"
							on:click|stopPropagation={() => handleDelete(job.id)}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-4"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
								/>
							</svg>
						</button>
					</div>
				</div>
			</a>
		{/each}
	</div>
{/if}
