<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';

	import { getQCProjects, createQCProject, deleteQCProject } from '$lib/apis/qc';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	dayjs.extend(relativeTime);

	const i18n = getContext('i18n');

	let projects: any[] = [];
	let loading = true;
	let query = '';

	let showCreate = false;
	let creating = false;
	let newName = '';
	let newDescription = '';

	$: filtered = query
		? projects.filter(
				(p) =>
					p.name.toLowerCase().includes(query.toLowerCase()) ||
					(p.description || '').toLowerCase().includes(query.toLowerCase())
			)
		: projects;

	const load = async () => {
		loading = true;
		try {
			projects = (await getQCProjects(localStorage.token)) || [];
		} catch (e) {
			toast.error(`${e}`);
		}
		loading = false;
	};

	const handleCreate = async () => {
		if (!newName.trim()) {
			toast.error($i18n.t('Project name is required'));
			return;
		}
		creating = true;
		try {
			await createQCProject(localStorage.token, {
				name: newName.trim(),
				description: newDescription.trim() || undefined
			});
			toast.success($i18n.t('Project created'));
			showCreate = false;
			newName = '';
			newDescription = '';
			await load();
		} catch (e) {
			toast.error(`${e}`);
		}
		creating = false;
	};

	const handleDelete = async (id: string) => {
		if (!confirm($i18n.t('Delete this project? Its jobs will be unlinked but not deleted.'))) return;
		try {
			await deleteQCProject(localStorage.token, id);
			toast.success($i18n.t('Project deleted'));
			await load();
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	onMount(load);
</script>

<div class="mt-1 mb-3 flex justify-between items-center gap-2">
	<div class="flex items-center gap-2 flex-1">
		<input
			type="text"
			placeholder={$i18n.t('Search Projects...')}
			bind:value={query}
			class="w-full max-w-md text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-1.5 outline-none"
		/>
	</div>
	<button
		class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-xl"
		on:click={() => (showCreate = true)}
	>
		+ {$i18n.t('New Project')}
	</button>
</div>

{#if showCreate}
	<div class="mb-4 p-4 rounded-xl border border-gray-200 dark:border-gray-800 space-y-3">
		<h3 class="text-sm font-medium">{$i18n.t('Create Project')}</h3>
		<input
			type="text"
			bind:value={newName}
			placeholder={$i18n.t('Project name')}
			class="w-full text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none"
		/>
		<textarea
			bind:value={newDescription}
			rows="2"
			placeholder={$i18n.t('Description (optional)')}
			class="w-full text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none"
		/>
		<div class="flex justify-end gap-2">
			<button
				class="px-3 py-1.5 text-sm rounded-xl border border-gray-200 dark:border-gray-800"
				on:click={() => (showCreate = false)}
				disabled={creating}
			>
				{$i18n.t('Cancel')}
			</button>
			<button
				class="px-3 py-1.5 text-sm font-medium bg-black text-white dark:bg-white dark:text-black rounded-xl disabled:opacity-50"
				on:click={handleCreate}
				disabled={creating}
			>
				{creating ? $i18n.t('Creating...') : $i18n.t('Create')}
			</button>
		</div>
	</div>
{/if}

{#if loading}
	<div class="flex justify-center py-12">
		<Spinner className="size-5" />
	</div>
{:else if filtered.length === 0}
	<div class="text-center text-gray-500 dark:text-gray-400 py-12">
		{query
			? $i18n.t('No projects match your search.')
			: $i18n.t('No projects yet. Use projects to group jobs across drawing revisions.')}
	</div>
{:else}
	<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
		{#each filtered as project}
			<a
				href="/qc/projects/{project.id}"
				class="block p-4 rounded-xl border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
				draggable="false"
			>
				<div class="flex justify-between items-start">
					<div class="flex-1 min-w-0">
						<h3 class="font-medium text-sm truncate">{project.name}</h3>
						{#if project.description}
							<p class="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
								{project.description}
							</p>
						{/if}
					</div>
				</div>
				<div class="flex items-center justify-between mt-3 text-xs text-gray-400">
					<span>{$i18n.t('Updated')} {dayjs(project.updated_at * 1000).fromNow()}</span>
					<Tooltip content={$i18n.t('Delete')}>
						<button
							class="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 transition"
							on:click|preventDefault|stopPropagation={() => handleDelete(project.id)}
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-3.5">
								<path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166M18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
							</svg>
						</button>
					</Tooltip>
				</div>
			</a>
		{/each}
	</div>
{/if}
