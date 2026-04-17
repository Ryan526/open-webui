<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import dayjs from 'dayjs';

	import { getJobSuppressionEvents, getQCSuppressionRules } from '$lib/apis/qc';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let jobId: string;

	let loading = true;
	let events: any[] = [];
	let rulesById: Record<string, any> = {};

	const load = async () => {
		loading = true;
		try {
			const [ev, rules] = await Promise.all([
				getJobSuppressionEvents(localStorage.token, jobId),
				getQCSuppressionRules(localStorage.token)
			]);
			events = ev || [];
			rulesById = {};
			for (const r of rules || []) rulesById[r.id] = r;
		} catch (e) {
			toast.error(`${e}`);
		}
		loading = false;
	};

	onMount(load);
</script>

<div class="flex flex-col h-full">
	<div class="px-3 py-2 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
		<h3 class="text-sm font-medium">{$i18n.t('Suppressed Findings')} ({events.length})</h3>
		<button class="text-xs text-blue-600 hover:underline" on:click={load}>{$i18n.t('Reload')}</button>
	</div>
	<div class="flex-1 overflow-y-auto">
		{#if loading}
			<div class="flex justify-center py-8"><Spinner className="size-5" /></div>
		{:else if events.length === 0}
			<div class="text-center text-gray-400 py-8 text-xs">
				{$i18n.t('Nothing was suppressed during this analysis.')}
			</div>
		{:else}
			<div class="divide-y divide-gray-100 dark:divide-gray-850">
				{#each events as ev}
					{@const rule = rulesById[ev.rule_id]}
					<div class="px-3 py-2.5">
						<div class="text-xs font-medium truncate">{ev.suppressed_title || $i18n.t('(untitled)')}</div>
						<div class="text-[11px] text-gray-500 mt-0.5">
							{#if ev.page_number}p.{ev.page_number} · {/if}
							{$i18n.t('Rule')}: {rule ? rule.name : ev.rule_id.slice(0, 8)}
							{#if rule}· {rule.scope}{/if}
						</div>
						<div class="text-[10px] text-gray-400 mt-0.5">
							{dayjs(ev.created_at * 1000).format('YYYY-MM-DD HH:mm')}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
