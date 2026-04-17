<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import dayjs from 'dayjs';

	import {
		getQCTemplateVersions,
		restoreQCTemplateVersion
	} from '$lib/apis/qc';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import VersionDiffDialog from './VersionDiffDialog.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let templateId: string;
	export let currentVersionId: string | null | undefined = null;

	let versions: any[] = [];
	let loading = true;
	let busy = false;

	let diffOpen = false;
	let diffA: number | null = null;
	let diffB: number | null = null;

	const load = async () => {
		loading = true;
		try {
			versions = (await getQCTemplateVersions(localStorage.token, templateId)) || [];
		} catch (e) {
			toast.error(`${e}`);
		}
		loading = false;
	};

	const compareWithCurrent = (v: any) => {
		const current = versions.find((x) => x.id === currentVersionId) || versions[0];
		if (!current) return;
		diffA = v.version_number;
		diffB = current.version_number;
		diffOpen = true;
	};

	const restore = async (v: any) => {
		if (!confirm($i18n.t('Restore template to v{{n}}? This creates a new version.', { n: v.version_number }))) return;
		busy = true;
		try {
			await restoreQCTemplateVersion(localStorage.token, templateId, v.version_number);
			toast.success($i18n.t('Restored to v{{n}}', { n: v.version_number }));
			dispatch('restored');
			await load();
		} catch (e) {
			toast.error(`${e}`);
		}
		busy = false;
	};

	onMount(load);
</script>

<div>
	<div class="flex items-center justify-between mb-2">
		<h3 class="text-sm font-medium">{$i18n.t('Version History')}</h3>
		<button class="text-xs text-blue-600 hover:underline" on:click={load}>{$i18n.t('Reload')}</button>
	</div>

	{#if loading}
		<div class="flex justify-center py-6"><Spinner className="size-4" /></div>
	{:else if versions.length === 0}
		<div class="text-xs text-gray-400 py-4">{$i18n.t('No versions yet.')}</div>
	{:else}
		<div class="rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
			<div class="grid grid-cols-[60px_130px_130px_1fr_130px] text-[11px] font-medium bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
				<div class="px-2 py-1.5">{$i18n.t('Version')}</div>
				<div class="px-2 py-1.5">{$i18n.t('Created')}</div>
				<div class="px-2 py-1.5">{$i18n.t('Source')}</div>
				<div class="px-2 py-1.5">{$i18n.t('Summary')}</div>
				<div class="px-2 py-1.5 text-right">{$i18n.t('Actions')}</div>
			</div>
			{#each versions as v}
				{@const isCurrent = v.id === currentVersionId}
				<div class="grid grid-cols-[60px_130px_130px_1fr_130px] text-xs border-b border-gray-100 dark:border-gray-850 last:border-0">
					<div class="px-2 py-2 font-medium">
						v{v.version_number}
						{#if isCurrent}
							<span class="ml-1 text-[10px] px-1 py-0.5 rounded bg-green-500/15 text-green-700 dark:text-green-400">now</span>
						{/if}
					</div>
					<div class="px-2 py-2 text-gray-500">{dayjs(v.created_at * 1000).fromNow()}</div>
					<div class="px-2 py-2 text-gray-500">{v.change_source}</div>
					<div class="px-2 py-2 text-gray-700 dark:text-gray-300 truncate">{v.change_summary || '—'}</div>
					<div class="px-2 py-2 text-right space-x-1">
						<button
							class="text-[11px] text-blue-600 hover:underline"
							on:click={() => {
								diffA = v.version_number;
								diffB = (versions[0] && versions[0].version_number) || v.version_number;
								diffOpen = true;
							}}
						>
							{$i18n.t('View')}
						</button>
						{#if !isCurrent}
							<button class="text-[11px] text-blue-600 hover:underline" on:click={() => compareWithCurrent(v)}>
								{$i18n.t('Compare')}
							</button>
							<button
								class="text-[11px] text-red-600 hover:underline disabled:opacity-50"
								on:click={() => restore(v)}
								disabled={busy}
							>
								{$i18n.t('Restore')}
							</button>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<VersionDiffDialog
	{templateId}
	{versions}
	bind:show={diffOpen}
	bind:a={diffA}
	bind:b={diffB}
/>
