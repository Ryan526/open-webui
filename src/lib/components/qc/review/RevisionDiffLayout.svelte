<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import {
		getQCJobById,
		getQCJobDocuments,
		getQCJobDiff,
		applyQCJobDiff
	} from '$lib/apis/qc';
	import DocumentViewer from './DocumentViewer.svelte';
	import SeverityBadge from '../SeverityBadge.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let prevJobId: string;
	export let newJobId: string;

	let prevJob: any = null;
	let newJob: any = null;
	let prevDocs: any[] = [];
	let newDocs: any[] = [];
	let diff: any = null;
	let loading = true;
	let applying = false;

	let prevDocIndex = 0;
	let newDocIndex = 0;
	let sharedPage = 1;
	let showAnnotated = true;
	let annotationOpacity = 0.8;

	let expanded = { carried_over: true, resolved: true, new: true };
	let createGhosts = false;

	$: prevFindingsOnPage = (diff?.carried_over || [])
		.map((e: any) => e.prev_finding)
		.concat((diff?.resolved || []).map((e: any) => e.prev_finding))
		.filter((f: any) => f && f.page_number === sharedPage && f.document_id === prevDocs[prevDocIndex]?.id);

	$: newFindingsOnPage = (diff?.carried_over || [])
		.map((e: any) => e.new_finding)
		.concat((diff?.new || []).map((e: any) => e.new_finding))
		.filter((f: any) => f && f.page_number === sharedPage && f.document_id === newDocs[newDocIndex]?.id);

	const load = async () => {
		loading = true;
		try {
			const [p, n, pd, nd, d] = await Promise.all([
				getQCJobById(localStorage.token, prevJobId),
				getQCJobById(localStorage.token, newJobId),
				getQCJobDocuments(localStorage.token, prevJobId),
				getQCJobDocuments(localStorage.token, newJobId),
				getQCJobDiff(localStorage.token, prevJobId, newJobId)
			]);
			if (!p || !n) {
				toast.error($i18n.t('Could not load one or both jobs'));
				goto('/qc/jobs');
				return;
			}
			prevJob = p;
			newJob = n;
			prevDocs = pd || [];
			newDocs = nd || [];
			diff = d;
		} catch (e) {
			toast.error(`${e}`);
		}
		loading = false;
	};

	const handleApply = async () => {
		applying = true;
		try {
			const res = await applyQCJobDiff(localStorage.token, prevJobId, newJobId, {
				create_resolved_ghosts: createGhosts
			});
			toast.success(
				$i18n.t('Diff applied: {{c}} carried over, {{n}} new, {{g}} resolved ghosts', {
					c: res?.carried_over_applied ?? 0,
					n: res?.new_tagged ?? 0,
					g: res?.resolved_ghosts_created ?? 0
				})
			);
			await load();
		} catch (e) {
			toast.error(`${e}`);
		}
		applying = false;
	};

	const navigate = (f: any, side: 'prev' | 'new') => {
		if (!f) return;
		sharedPage = f.page_number || 1;
		if (side === 'prev') {
			const idx = prevDocs.findIndex((d) => d.id === f.document_id);
			if (idx !== -1) prevDocIndex = idx;
		} else {
			const idx = newDocs.findIndex((d) => d.id === f.document_id);
			if (idx !== -1) newDocIndex = idx;
		}
	};

	onMount(load);
</script>

{#if loading}
	<div class="flex justify-center py-12"><Spinner className="size-5" /></div>
{:else if diff}
	<div class="flex flex-col" style="height: calc(100vh - 60px);">
		<!-- Header -->
		<div class="flex items-center justify-between gap-2 py-2 border-b border-gray-200 dark:border-gray-800">
			<div class="flex items-center gap-3 min-w-0">
				<button
					class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition shrink-0"
					on:click={() => goto(`/qc/jobs/${newJobId}`)}
				>
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
					</svg>
				</button>
				<div class="min-w-0">
					<div class="text-sm font-medium truncate">{$i18n.t('Revision Diff')}</div>
					<div class="text-xs text-gray-500 truncate">
						{prevJob.name} ({prevJob.revision_label || `Rev ${prevJob.revision_index ?? 0}`})
						→ {newJob.name} ({newJob.revision_label || `Rev ${newJob.revision_index ?? '?'}`})
					</div>
				</div>
			</div>
			<div class="flex items-center gap-2 shrink-0">
				<label class="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
					<input type="checkbox" bind:checked={createGhosts} />
					{$i18n.t('Create resolved ghosts')}
				</label>
				<button
					class="px-3 py-1 text-xs font-medium bg-black text-white dark:bg-white dark:text-black rounded-lg hover:opacity-90 disabled:opacity-50"
					disabled={applying}
					on:click={handleApply}
				>
					{applying ? $i18n.t('Applying...') : $i18n.t('Apply diff')}
				</button>
			</div>
		</div>

		<!-- Stats row -->
		<div class="flex gap-3 px-3 py-1.5 text-xs text-gray-600 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
			<span class="text-green-600 dark:text-green-400">{diff.stats.carried_over_count} carried over</span>
			<span class="text-red-600 dark:text-red-400">{diff.stats.resolved_count} resolved</span>
			<span class="text-blue-600 dark:text-blue-400">{diff.stats.new_count} new</span>
			{#if newJob.meta?.revision_diff_applied_at}
				<span class="ml-auto text-gray-500">{$i18n.t('Last applied')}: {new Date(newJob.meta.revision_diff_applied_at * 1000).toLocaleString()}</span>
			{/if}
		</div>

		<div class="flex flex-1 overflow-hidden">
			<!-- Left pane: prev job viewer -->
			<div class="flex-1 min-w-0 overflow-hidden flex flex-col border-r border-gray-200 dark:border-gray-800">
				<div class="px-3 py-1 text-xs text-gray-500 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
					{$i18n.t('Previous')}: {prevJob.revision_label || `Rev ${prevJob.revision_index ?? 0}`}
				</div>
				{#if prevDocs.length > 0}
					<div class="flex-1 overflow-hidden">
						<DocumentViewer
							documents={prevDocs}
							jobId={prevJobId}
							bind:selectedDocIndex={prevDocIndex}
							bind:selectedPage={sharedPage}
							bind:showAnnotated
							bind:annotationOpacity
							findings={prevFindingsOnPage}
						/>
					</div>
				{:else}
					<div class="p-4 text-xs text-gray-500">{$i18n.t('No documents on previous revision')}</div>
				{/if}
			</div>

			<!-- Right pane: new job viewer -->
			<div class="flex-1 min-w-0 overflow-hidden flex flex-col">
				<div class="px-3 py-1 text-xs text-gray-500 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
					{$i18n.t('New')}: {newJob.revision_label || `Rev ${newJob.revision_index ?? '?'}`}
				</div>
				{#if newDocs.length > 0}
					<div class="flex-1 overflow-hidden">
						<DocumentViewer
							documents={newDocs}
							jobId={newJobId}
							bind:selectedDocIndex={newDocIndex}
							bind:selectedPage={sharedPage}
							bind:showAnnotated
							bind:annotationOpacity
							findings={newFindingsOnPage}
						/>
					</div>
				{:else}
					<div class="p-4 text-xs text-gray-500">{$i18n.t('No documents on new revision')}</div>
				{/if}
			</div>

			<!-- Right side panel: diff categories -->
			<div class="w-[320px] shrink-0 border-l border-gray-200 dark:border-gray-800 overflow-y-auto">
				<!-- Carried over -->
				<div class="border-b border-gray-200 dark:border-gray-800">
					<button
						class="w-full flex justify-between items-center px-3 py-2 text-xs font-medium bg-gray-50 dark:bg-gray-900"
						on:click={() => (expanded.carried_over = !expanded.carried_over)}
					>
						<span class="text-green-700 dark:text-green-400">{$i18n.t('Carried over')} ({diff.stats.carried_over_count})</span>
						<span>{expanded.carried_over ? '−' : '+'}</span>
					</button>
					{#if expanded.carried_over}
						<div class="p-1">
							{#each diff.carried_over as entry}
								<button
									class="w-full text-left p-2 hover:bg-gray-100 dark:hover:bg-gray-850 rounded text-xs"
									on:click={() => navigate(entry.new_finding, 'new')}
								>
									<div class="flex gap-1 items-center">
										<SeverityBadge severity={entry.new_finding.severity} />
										<span class="truncate">#{entry.new_finding.finding_number} {entry.new_finding.title}</span>
									</div>
									<div class="text-[10px] text-gray-500 mt-0.5">
										p{entry.new_finding.page_number ?? '?'} · score {Math.round(entry.score * 100)}%
									</div>
								</button>
							{/each}
						</div>
					{/if}
				</div>
				<!-- Resolved -->
				<div class="border-b border-gray-200 dark:border-gray-800">
					<button
						class="w-full flex justify-between items-center px-3 py-2 text-xs font-medium bg-gray-50 dark:bg-gray-900"
						on:click={() => (expanded.resolved = !expanded.resolved)}
					>
						<span class="text-red-700 dark:text-red-400">{$i18n.t('Resolved')} ({diff.stats.resolved_count})</span>
						<span>{expanded.resolved ? '−' : '+'}</span>
					</button>
					{#if expanded.resolved}
						<div class="p-1">
							{#each diff.resolved as entry}
								<button
									class="w-full text-left p-2 hover:bg-gray-100 dark:hover:bg-gray-850 rounded text-xs"
									on:click={() => navigate(entry.prev_finding, 'prev')}
								>
									<div class="flex gap-1 items-center">
										<SeverityBadge severity={entry.prev_finding.severity} />
										<span class="truncate line-through text-gray-500">#{entry.prev_finding.finding_number} {entry.prev_finding.title}</span>
									</div>
									<div class="text-[10px] text-gray-500 mt-0.5">p{entry.prev_finding.page_number ?? '?'}</div>
								</button>
							{/each}
						</div>
					{/if}
				</div>
				<!-- New -->
				<div>
					<button
						class="w-full flex justify-between items-center px-3 py-2 text-xs font-medium bg-gray-50 dark:bg-gray-900"
						on:click={() => (expanded.new = !expanded.new)}
					>
						<span class="text-blue-700 dark:text-blue-400">{$i18n.t('New')} ({diff.stats.new_count})</span>
						<span>{expanded.new ? '−' : '+'}</span>
					</button>
					{#if expanded.new}
						<div class="p-1">
							{#each diff.new as entry}
								<button
									class="w-full text-left p-2 hover:bg-gray-100 dark:hover:bg-gray-850 rounded text-xs"
									on:click={() => navigate(entry.new_finding, 'new')}
								>
									<div class="flex gap-1 items-center">
										<SeverityBadge severity={entry.new_finding.severity} />
										<span class="truncate">#{entry.new_finding.finding_number} {entry.new_finding.title}</span>
									</div>
									<div class="text-[10px] text-gray-500 mt-0.5">p{entry.new_finding.page_number ?? '?'}</div>
								</button>
							{/each}
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}
