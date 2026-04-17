<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import dayjs from 'dayjs';

	import {
		getQCSuppressionRules,
		deleteQCSuppressionRule,
		getQCTemplates,
		getQCProjects
	} from '$lib/apis/qc';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import SuppressionRuleEditor from './SuppressionRuleEditor.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let rules: any[] = [];
	let templateChoices: { id: string; name: string }[] = [];
	let projectChoices: { id: string; name: string }[] = [];

	let showEditor = false;
	let editing: any | null = null;

	const load = async () => {
		loading = true;
		try {
			const [rs, ts, ps] = await Promise.all([
				getQCSuppressionRules(localStorage.token),
				getQCTemplates(localStorage.token),
				getQCProjects(localStorage.token)
			]);
			rules = rs || [];
			templateChoices = (ts || []).map((t: any) => ({ id: t.id, name: t.name }));
			projectChoices = (ps || []).map((p: any) => ({ id: p.id, name: p.name }));
		} catch (e) {
			toast.error(`${e}`);
		}
		loading = false;
	};

	const edit = (r: any) => {
		editing = r;
		showEditor = true;
	};

	const create = () => {
		editing = null;
		showEditor = true;
	};

	const del = async (id: string) => {
		if (!confirm($i18n.t('Delete this suppression rule?'))) return;
		try {
			await deleteQCSuppressionRule(localStorage.token, id);
			toast.success($i18n.t('Rule deleted'));
			await load();
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	onMount(load);
</script>

<div class="mt-1 mb-3 flex justify-between items-center gap-2">
	<h2 class="text-sm font-medium">{$i18n.t('Suppression Rules')}</h2>
	<button
		class="px-3 py-1 text-xs font-medium bg-black text-white dark:bg-white dark:text-black rounded-xl"
		on:click={create}
	>
		+ {$i18n.t('New Rule')}
	</button>
</div>

{#if loading}
	<div class="flex justify-center py-12"><Spinner className="size-5" /></div>
{:else if rules.length === 0}
	<div class="text-center text-gray-500 dark:text-gray-400 py-12 text-sm">
		{$i18n.t('No suppression rules configured.')}
	</div>
{:else}
	<div class="space-y-2">
		{#each rules as r}
			<div class="p-3 rounded-xl border border-gray-200 dark:border-gray-800 flex items-center gap-3">
				<div class="flex-1 min-w-0">
					<div class="flex items-center gap-2 flex-wrap">
						<span class="font-medium text-sm truncate">{r.name}</span>
						<span class="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 uppercase">{r.scope}</span>
						<span class="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-700 dark:text-blue-400">{r.match_type}</span>
						{#if r.enabled === 0}
							<span class="text-[10px] px-1.5 py-0.5 rounded bg-red-500/15 text-red-700 dark:text-red-400">disabled</span>
						{/if}
					</div>
					<div class="text-xs text-gray-500 mt-0.5 truncate">{r.match_value}</div>
					<div class="text-[10px] text-gray-400 mt-0.5">
						{$i18n.t('Hits')}: {r.hit_count}
						{#if r.last_hit_at}· {$i18n.t('Last hit')} {dayjs(r.last_hit_at * 1000).fromNow()}{/if}
					</div>
				</div>
				<button class="px-2 py-1 text-xs rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800" on:click={() => edit(r)}>{$i18n.t('Edit')}</button>
				<button class="px-2 py-1 text-xs rounded border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20" on:click={() => del(r.id)}>{$i18n.t('Delete')}</button>
			</div>
		{/each}
	</div>
{/if}

<SuppressionRuleEditor
	bind:show={showEditor}
	rule={editing}
	{templateChoices}
	{projectChoices}
	on:saved={load}
/>
