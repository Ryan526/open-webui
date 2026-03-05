<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';

	import { getQCTemplates, deleteQCTemplate, cloneQCTemplate } from '$lib/apis/qc';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	dayjs.extend(relativeTime);

	const i18n = getContext('i18n');

	let templates: any[] = [];
	let loading = true;
	let query = '';

	$: filteredTemplates = query
		? templates.filter(
				(t) =>
					t.name.toLowerCase().includes(query.toLowerCase()) ||
					(t.description || '').toLowerCase().includes(query.toLowerCase())
			)
		: templates;

	const loadTemplates = async () => {
		loading = true;
		try {
			templates = (await getQCTemplates(localStorage.token)) || [];
		} catch (e) {
			toast.error(`${e}`);
		}
		loading = false;
	};

	const handleDelete = async (id: string) => {
		if (!confirm('Are you sure you want to delete this template?')) return;
		try {
			await deleteQCTemplate(localStorage.token, id);
			toast.success($i18n.t('Template deleted'));
			await loadTemplates();
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const handleClone = async (id: string) => {
		try {
			const cloned = await cloneQCTemplate(localStorage.token, id);
			if (cloned) {
				toast.success($i18n.t('Template cloned'));
				await loadTemplates();
			}
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	onMount(loadTemplates);
</script>

<div class="mt-1 mb-3 flex justify-between items-center gap-2">
	<div class="flex items-center gap-2 flex-1">
		<input
			type="text"
			placeholder={$i18n.t('Search Templates...')}
			bind:value={query}
			class="w-full max-w-md text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-1.5 outline-none"
		/>
	</div>
	<button
		class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-xl"
		on:click={() => goto('/qc/templates/create')}
	>
		+ {$i18n.t('Create Template')}
	</button>
</div>

{#if loading}
	<div class="flex justify-center py-12">
		<Spinner className="size-5" />
	</div>
{:else if filteredTemplates.length === 0}
	<div class="text-center text-gray-500 dark:text-gray-400 py-12">
		{query ? $i18n.t('No templates match your search.') : $i18n.t('No templates yet. Create one to get started.')}
	</div>
{:else}
	<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
		{#each filteredTemplates as template}
			<a
				href="/qc/templates/{template.id}"
				class="block p-4 rounded-xl border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
				draggable="false"
			>
				<div class="flex justify-between items-start">
					<div class="flex-1 min-w-0">
						<h3 class="font-medium text-sm truncate">{template.name}</h3>
						{#if template.description}
							<p class="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
								{template.description}
							</p>
						{/if}
					</div>
				</div>

				<div class="flex items-center justify-between mt-3 text-xs text-gray-400">
					<span>{template.model_id || 'No model set'}</span>
					<span>{dayjs(template.updated_at * 1000).fromNow()}</span>
				</div>

				<div class="flex gap-1 mt-2">
					<Tooltip content={$i18n.t('Clone')}>
						<button
							class="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition"
							on:click|stopPropagation={() => handleClone(template.id)}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-3.5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 0 1-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 0 1 1.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 0 0-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 0 1-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 0 0-3.375-3.375h-1.5a1.125 1.125 0 0 1-1.125-1.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H9.75"
								/>
							</svg>
						</button>
					</Tooltip>
					<Tooltip content={$i18n.t('Delete')}>
						<button
							class="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 transition"
							on:click|stopPropagation={() => handleDelete(template.id)}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-3.5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
								/>
							</svg>
						</button>
					</Tooltip>
				</div>
			</a>
		{/each}
	</div>
{/if}
