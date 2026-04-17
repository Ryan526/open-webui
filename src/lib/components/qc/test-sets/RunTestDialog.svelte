<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';

	import {
		getQCTemplates,
		getQCTemplateVersions,
		runQCTestSet
	} from '$lib/apis/qc';
	import { models } from '$lib/stores';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let testSetId: string;
	export let show: boolean = false;

	let templates: any[] = [];
	let versions: any[] = [];
	let loading = true;
	let running = false;

	let selectedTemplateId = '';
	let selectedVersionId = '';
	let modelOverride = '';

	const load = async () => {
		loading = true;
		try {
			templates = (await getQCTemplates(localStorage.token)) || [];
		} catch (e) {
			toast.error(`${e}`);
		}
		loading = false;
	};

	const loadVersions = async (tplId: string) => {
		if (!tplId) {
			versions = [];
			return;
		}
		try {
			versions = (await getQCTemplateVersions(localStorage.token, tplId)) || [];
		} catch {
			versions = [];
		}
	};

	let lastTplId = '';
	$: if (selectedTemplateId !== lastTplId) {
		lastTplId = selectedTemplateId;
		selectedVersionId = '';
		loadVersions(selectedTemplateId);
	}

	const run = async () => {
		if (!selectedTemplateId) {
			toast.error($i18n.t('Template is required'));
			return;
		}
		running = true;
		try {
			const res = await runQCTestSet(localStorage.token, testSetId, {
				template_id: selectedTemplateId,
				template_version_id: selectedVersionId || undefined,
				model_id_override: modelOverride || undefined
			});
			toast.success($i18n.t('Test run started'));
			show = false;
			dispatch('started', res);
			if (res?.id) goto(`/qc/test-runs/${res.id}`);
		} catch (e) {
			toast.error(`${e}`);
		}
		running = false;
	};

	onMount(() => {
		if (show) load();
	});
	$: if (show && templates.length === 0 && !loading) load();
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
			class="w-[min(480px,calc(100vw-2rem))] bg-white dark:bg-gray-900 rounded-2xl shadow-xl"
			on:click|stopPropagation
			role="dialog"
		>
			<div class="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
				<h3 class="text-sm font-medium">{$i18n.t('Run Test Set')}</h3>
				<button class="text-xs text-gray-500 hover:text-gray-700" on:click={() => (show = false)}>✕</button>
			</div>
			<div class="p-4 space-y-3">
				<div>
					<label class="block text-xs text-gray-500 mb-1" for="rt-tpl">{$i18n.t('Template')}</label>
					<select
						id="rt-tpl"
						bind:value={selectedTemplateId}
						class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
					>
						<option value="">{$i18n.t('Select...')}</option>
						{#each templates as t}
							<option value={t.id}>{t.name}</option>
						{/each}
					</select>
				</div>
				{#if selectedTemplateId && versions.length > 0}
					<div>
						<label class="block text-xs text-gray-500 mb-1" for="rt-ver">{$i18n.t('Version (default: current)')}</label>
						<select
							id="rt-ver"
							bind:value={selectedVersionId}
							class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
						>
							<option value="">{$i18n.t('Current')}</option>
							{#each versions as v}
								<option value={v.id}>v{v.version_number} ({v.change_source})</option>
							{/each}
						</select>
					</div>
				{/if}
				<div>
					<label class="block text-xs text-gray-500 mb-1" for="rt-model">{$i18n.t('Model override (optional)')}</label>
					<select
						id="rt-model"
						bind:value={modelOverride}
						class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
					>
						<option value="">{$i18n.t('Use template default')}</option>
						{#each $models as m}
							<option value={m.id}>{m.name || m.id}</option>
						{/each}
					</select>
				</div>
				<div class="flex justify-end gap-2 pt-2">
					<button class="px-3 py-1.5 text-sm rounded-xl border border-gray-200 dark:border-gray-800" on:click={() => (show = false)} disabled={running}>
						{$i18n.t('Cancel')}
					</button>
					<button class="px-3 py-1.5 text-sm font-medium bg-black text-white dark:bg-white dark:text-black rounded-xl disabled:opacity-50" on:click={run} disabled={running}>
						{running ? $i18n.t('Starting...') : $i18n.t('Run')}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
