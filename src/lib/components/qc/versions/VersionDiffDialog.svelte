<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, createEventDispatcher } from 'svelte';

	import { diffQCTemplateVersions } from '$lib/apis/qc';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let templateId: string;
	export let show: boolean = false;
	export let versions: any[] = [];
	export let a: number | null = null;
	export let b: number | null = null;

	let diff: any = null;
	let loading = false;

	// Hand-rolled LCS-based line diff (~30 LOC)
	const lineDiff = (
		left: string,
		right: string
	): { type: 'eq' | 'add' | 'del'; text: string }[] => {
		const A = (left || '').split(/\n/);
		const B = (right || '').split(/\n/);
		const m = A.length;
		const n = B.length;
		// LCS table
		const lcs: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
		for (let i = m - 1; i >= 0; i--) {
			for (let j = n - 1; j >= 0; j--) {
				if (A[i] === B[j]) lcs[i][j] = 1 + lcs[i + 1][j + 1];
				else lcs[i][j] = Math.max(lcs[i + 1][j], lcs[i][j + 1]);
			}
		}
		const out: { type: 'eq' | 'add' | 'del'; text: string }[] = [];
		let i = 0;
		let j = 0;
		while (i < m && j < n) {
			if (A[i] === B[j]) {
				out.push({ type: 'eq', text: A[i] });
				i++;
				j++;
			} else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
				out.push({ type: 'del', text: A[i] });
				i++;
			} else {
				out.push({ type: 'add', text: B[j] });
				j++;
			}
		}
		while (i < m) out.push({ type: 'del', text: A[i++] });
		while (j < n) out.push({ type: 'add', text: B[j++] });
		return out;
	};

	const load = async () => {
		if (a == null || b == null) return;
		loading = true;
		try {
			diff = await diffQCTemplateVersions(localStorage.token, templateId, a, b);
		} catch (e) {
			toast.error(`${e}`);
		}
		loading = false;
	};

	$: if (show && a != null && b != null) load();
	$: spDiff = diff ? lineDiff(diff.a?.system_prompt || '', diff.b?.system_prompt || '') : [];

	const checklistOf = (v: any): any[] => (v?.meta?.checklist as any[]) || [];
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
			class="w-[min(960px,calc(100vw-2rem))] max-h-[85vh] overflow-hidden bg-white dark:bg-gray-900 rounded-2xl shadow-xl flex flex-col"
			on:click|stopPropagation
			role="dialog"
		>
			<div class="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
				<div>
					<h3 class="text-sm font-medium">{$i18n.t('Version Diff')}</h3>
					<div class="flex items-center gap-2 text-xs text-gray-500 mt-1">
						<span>{$i18n.t('From')}</span>
						<select
							bind:value={a}
							class="text-xs rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1 outline-none"
						>
							{#each versions as v}
								<option value={v.version_number}>v{v.version_number} ({v.change_source})</option>
							{/each}
						</select>
						<span>→</span>
						<select
							bind:value={b}
							class="text-xs rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1 outline-none"
						>
							{#each versions as v}
								<option value={v.version_number}>v{v.version_number} ({v.change_source})</option>
							{/each}
						</select>
					</div>
				</div>
				<button class="text-xs text-gray-500 hover:text-gray-700" on:click={() => (show = false)}>✕</button>
			</div>

			<div class="flex-1 overflow-y-auto p-3 space-y-4">
				{#if loading || !diff}
					<div class="flex justify-center py-8"><Spinner className="size-5" /></div>
				{:else}
					<!-- system_prompt unified line diff -->
					<div>
						<h4 class="text-xs font-medium mb-1">{$i18n.t('System Prompt')}</h4>
						<div class="text-[11px] font-mono rounded-lg border border-gray-200 dark:border-gray-800 overflow-auto max-h-72">
							{#each spDiff as line}
								<div
									class="whitespace-pre-wrap px-2 py-0.5 {line.type === 'add'
										? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300'
										: line.type === 'del'
											? 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-300 line-through'
											: ''}"
								>
									<span class="text-gray-400 mr-1 select-none">{line.type === 'add' ? '+' : line.type === 'del' ? '-' : ' '}</span>{line.text || '\u00A0'}
								</div>
							{/each}
						</div>
					</div>

					<!-- Checklist side-by-side -->
					<div>
						<h4 class="text-xs font-medium mb-1">{$i18n.t('Checklist')}</h4>
						<div class="grid grid-cols-2 gap-3">
							<div>
								<div class="text-[11px] text-gray-500 mb-1">v{diff.a.version_number}</div>
								<ul class="space-y-1 text-xs">
									{#each checklistOf(diff.a) as item}
										<li class="px-2 py-1 rounded-lg bg-gray-50 dark:bg-gray-850">
											<span class="font-medium">{item.label || item.name || item.id}</span>
											{#if item.description}<span class="text-gray-500"> — {item.description}</span>{/if}
										</li>
									{:else}
										<li class="text-gray-400 text-[11px]">{$i18n.t('Empty')}</li>
									{/each}
								</ul>
							</div>
							<div>
								<div class="text-[11px] text-gray-500 mb-1">v{diff.b.version_number}</div>
								<ul class="space-y-1 text-xs">
									{#each checklistOf(diff.b) as item}
										<li class="px-2 py-1 rounded-lg bg-gray-50 dark:bg-gray-850">
											<span class="font-medium">{item.label || item.name || item.id}</span>
											{#if item.description}<span class="text-gray-500"> — {item.description}</span>{/if}
										</li>
									{:else}
										<li class="text-gray-400 text-[11px]">{$i18n.t('Empty')}</li>
									{/each}
								</ul>
							</div>
						</div>
					</div>

					<!-- Other key fields -->
					<div class="grid grid-cols-2 gap-3 text-xs">
						<div class="rounded-lg border border-gray-200 dark:border-gray-800 p-2">
							<div class="text-[11px] text-gray-500 mb-0.5">{$i18n.t('Model')}</div>
							<div>{diff.a.model_id || '—'}</div>
						</div>
						<div class="rounded-lg border border-gray-200 dark:border-gray-800 p-2">
							<div class="text-[11px] text-gray-500 mb-0.5">{$i18n.t('Model')}</div>
							<div>{diff.b.model_id || '—'}</div>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
