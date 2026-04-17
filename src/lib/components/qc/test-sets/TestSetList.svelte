<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import dayjs from 'dayjs';

	import {
		getQCTestSets,
		createQCTestSet,
		deleteQCTestSet
	} from '$lib/apis/qc';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let sets: any[] = [];
	let loading = true;
	let showCreate = false;
	let creating = false;
	let newName = '';
	let newDescription = '';

	const load = async () => {
		loading = true;
		try {
			sets = (await getQCTestSets(localStorage.token)) || [];
		} catch (e) {
			toast.error(`${e}`);
		}
		loading = false;
	};

	const handleCreate = async () => {
		if (!newName.trim()) {
			toast.error($i18n.t('Name is required'));
			return;
		}
		creating = true;
		try {
			const res = await createQCTestSet(localStorage.token, {
				name: newName.trim(),
				description: newDescription.trim() || undefined
			});
			toast.success($i18n.t('Test set created'));
			if (res?.id) goto(`/qc/test-sets/${res.id}`);
			else await load();
		} catch (e) {
			toast.error(`${e}`);
		}
		creating = false;
	};

	const handleDelete = async (id: string) => {
		if (!confirm($i18n.t('Delete this test set?'))) return;
		try {
			await deleteQCTestSet(localStorage.token, id);
			toast.success($i18n.t('Test set deleted'));
			await load();
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	onMount(load);
</script>

<div class="mt-1 mb-3 flex justify-between items-center gap-2">
	<h2 class="text-sm font-medium">{$i18n.t('Test Sets')}</h2>
	<button
		class="px-3 py-1 text-xs font-medium bg-black text-white dark:bg-white dark:text-black rounded-xl"
		on:click={() => (showCreate = !showCreate)}
	>
		+ {$i18n.t('New Test Set')}
	</button>
</div>

{#if showCreate}
	<div class="mb-4 p-4 rounded-xl border border-gray-200 dark:border-gray-800 space-y-3">
		<input
			type="text"
			bind:value={newName}
			placeholder={$i18n.t('Test set name')}
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
	<div class="flex justify-center py-12"><Spinner className="size-5" /></div>
{:else if sets.length === 0}
	<div class="text-center text-gray-500 py-12 text-sm">
		{$i18n.t('No test sets yet. Create one to benchmark templates against golden findings.')}
	</div>
{:else}
	<div class="space-y-2">
		{#each sets as s}
			<a
				href="/qc/test-sets/{s.id}"
				class="flex items-center gap-3 p-3 rounded-xl border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
			>
				<div class="flex-1 min-w-0">
					<div class="font-medium text-sm truncate">{s.name}</div>
					{#if s.description}
						<div class="text-xs text-gray-500 truncate">{s.description}</div>
					{/if}
				</div>
				<span class="text-xs text-gray-400">{dayjs(s.updated_at * 1000).fromNow()}</span>
				<button
					class="px-2 py-1 text-xs rounded border border-red-300 dark:border-red-700 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
					on:click|preventDefault|stopPropagation={() => handleDelete(s.id)}
				>
					{$i18n.t('Delete')}
				</button>
			</a>
		{/each}
	</div>
{/if}
