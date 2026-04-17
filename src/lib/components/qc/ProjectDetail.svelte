<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';

	import {
		getQCProjectById,
		updateQCProject,
		deleteQCProject
	} from '$lib/apis/qc';
	import JobStatusBadge from './JobStatusBadge.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	dayjs.extend(relativeTime);

	const i18n = getContext('i18n');

	export let projectId: string;

	let project: any = null;
	let jobs: any[] = [];
	let loading = true;
	let editing = false;

	let name = '';
	let description = '';

	const load = async () => {
		loading = true;
		try {
			const res = await getQCProjectById(localStorage.token, projectId);
			if (!res) {
				toast.error($i18n.t('Project not found'));
				goto('/qc/projects');
				return;
			}
			project = res;
			jobs = res.jobs || [];
			name = project.name;
			description = project.description || '';
		} catch (e) {
			toast.error(`${e}`);
		}
		loading = false;
	};

	const handleSave = async () => {
		if (!name.trim()) {
			toast.error($i18n.t('Name is required'));
			return;
		}
		try {
			await updateQCProject(localStorage.token, projectId, {
				name: name.trim(),
				description: description.trim() || undefined
			});
			toast.success($i18n.t('Saved'));
			editing = false;
			await load();
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const handleDelete = async () => {
		if (!confirm($i18n.t('Delete this project?'))) return;
		try {
			await deleteQCProject(localStorage.token, projectId);
			toast.success($i18n.t('Project deleted'));
			goto('/qc/projects');
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const openDiff = (prevId: string, newId: string) => {
		goto(`/qc/jobs/${prevId}/diff/${newId}`);
	};

	onMount(load);
</script>

{#if loading}
	<div class="flex justify-center py-12"><Spinner className="size-5" /></div>
{:else if project}
	<div class="py-3">
		<button
			class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition flex items-center gap-1 mb-4"
			on:click={() => goto('/qc/projects')}
		>
			<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4">
				<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
			</svg>
			{$i18n.t('Back to Projects')}
		</button>

		{#if editing}
			<div class="space-y-3 mb-6">
				<input
					type="text"
					bind:value={name}
					class="w-full text-lg font-medium rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none"
				/>
				<textarea
					bind:value={description}
					rows="2"
					placeholder={$i18n.t('Description')}
					class="w-full text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none"
				/>
				<div class="flex justify-end gap-2">
					<button class="px-3 py-1.5 text-sm rounded-xl border border-gray-200 dark:border-gray-800" on:click={() => (editing = false)}>
						{$i18n.t('Cancel')}
					</button>
					<button class="px-3 py-1.5 text-sm font-medium bg-black text-white dark:bg-white dark:text-black rounded-xl" on:click={handleSave}>
						{$i18n.t('Save')}
					</button>
				</div>
			</div>
		{:else}
			<div class="flex justify-between items-start gap-3 mb-6">
				<div class="flex-1 min-w-0">
					<h2 class="text-lg font-medium">{project.name}</h2>
					{#if project.description}
						<p class="text-sm text-gray-500 mt-1">{project.description}</p>
					{/if}
				</div>
				<div class="flex gap-2 shrink-0">
					<button
						class="px-3 py-1 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
						on:click={() => (editing = true)}
					>
						{$i18n.t('Edit')}
					</button>
					<button
						class="px-3 py-1 text-xs rounded-lg border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
						on:click={handleDelete}
					>
						{$i18n.t('Delete')}
					</button>
				</div>
			</div>
		{/if}

		<h3 class="text-sm font-medium mb-2">{$i18n.t('Revisions')} ({jobs.length})</h3>
		{#if jobs.length === 0}
			<div class="text-sm text-gray-500 py-4 border border-dashed border-gray-300 dark:border-gray-700 rounded-xl text-center">
				{$i18n.t('No jobs yet. Create a QC job and assign it to this project.')}
			</div>
		{:else}
			<div class="space-y-2">
				{#each jobs as job, idx}
					<div class="p-3 rounded-xl border border-gray-200 dark:border-gray-800 flex items-center gap-3">
						<div class="shrink-0 w-16 text-xs text-gray-500">
							{job.revision_index !== null && job.revision_index !== undefined
								? `Rev ${job.revision_index}`
								: $i18n.t('Base')}
							{#if job.revision_label}
								<div class="text-[10px] truncate">{job.revision_label}</div>
							{/if}
						</div>
						<a href="/qc/jobs/{job.id}" class="flex-1 min-w-0">
							<div class="font-medium text-sm truncate">{job.name}</div>
							<div class="text-xs text-gray-500">{dayjs(job.updated_at * 1000).fromNow()}</div>
						</a>
						<JobStatusBadge status={job.status} result={job.overall_result} />
						{#if idx > 0}
							<select
								class="text-xs rounded-lg border border-gray-200 dark:border-gray-700 bg-transparent px-2 py-1"
								on:change={(e) => {
									const target = e.target as HTMLSelectElement;
									if (target.value) openDiff(target.value, job.id);
									target.value = '';
								}}
							>
								<option value="">{$i18n.t('Compare to...')}</option>
								{#each jobs.slice(0, idx) as other}
									<option value={other.id}>
										{other.revision_index !== null && other.revision_index !== undefined
											? `Rev ${other.revision_index}`
											: $i18n.t('Base')}
										{other.revision_label ? `· ${other.revision_label}` : ''}
									</option>
								{/each}
							</select>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}
