<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import {
		getQCJobById,
		getQCJobDocuments,
		getQCFindings,
		runQCJob,
		addQCJobDocument,
		exportQCJob,
		selfImproveQCTemplate
	} from '$lib/apis/qc';

	import DocumentViewer from './DocumentViewer.svelte';
	import FindingsPanel from './FindingsPanel.svelte';
	import JobStatusBadge from '../JobStatusBadge.svelte';
	import SelfImproveDialog from './SelfImproveDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let jobId: string;

	let job: any = null;
	let documents: any[] = [];
	let findings: any[] = [];
	let loading = true;
	let running = false;

	let selectedDocIndex = 0;
	let selectedPage = 1;
	let showAnnotated = true;

	let fileInput: HTMLInputElement;

	let pollInterval: number | null = null;

	// Self-improve state
	let selfImproveLoading = false;
	let selfImproveSuggestions: any = null;
	let showSelfImproveDialog = false;

	$: selectedDoc = documents[selectedDocIndex] || null;
	$: pageFindings = findings.filter(
		(f) =>
			f.document_id === selectedDoc?.id && f.page_number === selectedPage
	);

	$: canSelfImprove =
		job?.status === 'completed' &&
		job?.template_id &&
		findings.some((f) => f.status === 'confirmed' || f.status === 'dismissed');

	const loadJob = async () => {
		try {
			job = await getQCJobById(localStorage.token, jobId);
			if (!job) {
				toast.error($i18n.t('Job not found'));
				goto('/qc/jobs');
				return;
			}
			documents = (await getQCJobDocuments(localStorage.token, jobId)) || [];
			findings = (await getQCFindings(localStorage.token, jobId)) || [];

			// If job is running, poll for updates
			if (job.status === 'running' && !pollInterval) {
				pollInterval = setInterval(async () => {
					await loadJob();
					if (job && job.status !== 'running') {
						clearInterval(pollInterval!);
						pollInterval = null;
					}
				}, 5000) as unknown as number;
			}
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const handleRun = async () => {
		running = true;
		try {
			await runQCJob(localStorage.token, jobId);
			toast.success($i18n.t('QC analysis started'));
			await loadJob();
		} catch (e) {
			toast.error(`${e}`);
		}
		running = false;
	};

	const handleUploadMore = async () => {
		fileInput?.click();
	};

	const handleFileUpload = async (event: Event) => {
		const input = event.target as HTMLInputElement;
		if (!input.files) return;

		for (const file of Array.from(input.files)) {
			try {
				await addQCJobDocument(localStorage.token, jobId, file, 'subject');
				toast.success(`${file.name} uploaded`);
			} catch (e) {
				toast.error(`Failed to upload ${file.name}: ${e}`);
			}
		}
		await loadJob();
		input.value = '';
	};

	const handleExport = async (format: string) => {
		try {
			const result = await exportQCJob(localStorage.token, jobId, format);
			if (format === 'csv' && result instanceof Blob) {
				const url = URL.createObjectURL(result);
				const a = document.createElement('a');
				a.href = url;
				a.download = `qc_job_${jobId}.csv`;
				a.click();
				URL.revokeObjectURL(url);
			} else if (format === 'json') {
				const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
				const url = URL.createObjectURL(blob);
				const a = document.createElement('a');
				a.href = url;
				a.download = `qc_job_${jobId}.json`;
				a.click();
				URL.revokeObjectURL(url);
			}
			toast.success($i18n.t('Export complete'));
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const handleSelfImprove = async () => {
		selfImproveLoading = true;
		try {
			selfImproveSuggestions = await selfImproveQCTemplate(localStorage.token, jobId);
			showSelfImproveDialog = true;
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			selfImproveLoading = false;
		}
	};

	const navigateToFinding = (finding: any) => {
		// Find the document and page for this finding
		if (finding.document_id) {
			const docIdx = documents.findIndex((d) => d.id === finding.document_id);
			if (docIdx !== -1) selectedDocIndex = docIdx;
		}
		if (finding.page_number) {
			selectedPage = finding.page_number;
		}
	};

	onMount(async () => {
		await loadJob();
		loading = false;

		return () => {
			if (pollInterval) clearInterval(pollInterval);
		};
	});
</script>

<input
	bind:this={fileInput}
	type="file"
	multiple
	accept=".pdf,.png,.jpg,.jpeg,.tiff,.xlsx,.docx"
	class="hidden"
	on:change={handleFileUpload}
/>

{#if loading}
	<div class="flex justify-center py-12">
		<Spinner className="size-5" />
	</div>
{:else if job}
	<!-- Header -->
	<div class="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-800">
		<div class="flex items-center gap-3 min-w-0">
			<button
				class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition shrink-0"
				on:click={() => goto('/qc/jobs')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="size-5"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
				</svg>
			</button>
			<h2 class="font-medium text-sm truncate">{job.name}</h2>
			<JobStatusBadge status={job.status} result={job.overall_result} />
		</div>

		<div class="flex items-center gap-2 shrink-0">
			{#if job.status === 'running'}
				<div class="flex items-center gap-2 text-sm text-blue-600">
					<Spinner className="size-4" />
					{$i18n.t('Analyzing...')}
				</div>
			{:else}
				<button
					class="px-3 py-1 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
					on:click={handleUploadMore}
				>
					+ {$i18n.t('Add Document')}
				</button>

				<button
					class="px-3 py-1 text-xs font-medium bg-black text-white dark:bg-white dark:text-black rounded-lg hover:opacity-90 transition disabled:opacity-50"
					disabled={running || documents.length === 0 || !job.model_id}
					on:click={handleRun}
				>
					{running ? $i18n.t('Starting...') : $i18n.t('Run Analysis')}
				</button>

				{#if job.status === 'completed'}
					{#if canSelfImprove}
						<button
							class="px-3 py-1 text-xs rounded-lg border border-purple-300 dark:border-purple-700 text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20 transition disabled:opacity-50 flex items-center gap-1.5"
							disabled={selfImproveLoading}
							on:click={handleSelfImprove}
						>
							{#if selfImproveLoading}
								<Spinner className="size-3" />
							{:else}
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
										d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
									/>
								</svg>
							{/if}
							{selfImproveLoading ? $i18n.t('Analyzing...') : $i18n.t('Improve Template')}
						</button>
					{/if}

					<button
						class="px-3 py-1 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
						on:click={() => handleExport('csv')}
					>
						{$i18n.t('Export CSV')}
					</button>
					<button
						class="px-3 py-1 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
						on:click={() => handleExport('json')}
					>
						{$i18n.t('Export JSON')}
					</button>
				{/if}
			{/if}
		</div>
	</div>

	{#if documents.length === 0}
		<!-- No documents - show upload prompt -->
		<div class="flex items-center justify-center py-20">
			<div class="text-center">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1"
					stroke="currentColor"
					class="size-12 mx-auto text-gray-300 dark:text-gray-600 mb-4"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m6.75 12-3-3m0 0-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
					/>
				</svg>
				<p class="text-gray-500 dark:text-gray-400 mb-4">
					{$i18n.t('Upload documents to begin QC analysis')}
				</p>
				<button
					class="px-4 py-2 text-sm font-medium bg-black text-white dark:bg-white dark:text-black rounded-xl hover:opacity-90 transition"
					on:click={handleUploadMore}
				>
					{$i18n.t('Upload Documents')}
				</button>
			</div>
		</div>
	{:else}
		<!-- Split pane: Document viewer + Findings panel -->
		<div class="flex gap-0 flex-1 overflow-hidden" style="height: calc(100vh - 120px);">
			<!-- Document Viewer (70%) -->
			<div class="flex-1 min-w-0 overflow-hidden">
				<DocumentViewer
					{documents}
					{jobId}
					bind:selectedDocIndex
					bind:selectedPage
					bind:showAnnotated
				/>
			</div>

			<!-- Findings Panel (30%) -->
			<div class="w-[360px] shrink-0 border-l border-gray-200 dark:border-gray-800 overflow-hidden">
				<FindingsPanel
					{findings}
					{jobId}
					{selectedDoc}
					{selectedPage}
					on:navigate={(e) => navigateToFinding(e.detail)}
					on:refresh={loadJob}
				/>
			</div>
		</div>
	{/if}

	<!-- Statistics bar -->
	{#if job.meta?.statistics}
		<div
			class="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 px-4 py-1.5 flex items-center gap-4 text-xs text-gray-500 z-10"
		>
			<span>{job.meta.statistics.pages_analyzed || 0} pages analyzed</span>
			{#if job.meta.statistics.critical_count > 0}
				<span class="text-red-600">{job.meta.statistics.critical_count} critical</span>
			{/if}
			{#if job.meta.statistics.major_count > 0}
				<span class="text-orange-600">{job.meta.statistics.major_count} major</span>
			{/if}
			{#if job.meta.statistics.minor_count > 0}
				<span class="text-yellow-600">{job.meta.statistics.minor_count} minor</span>
			{/if}
			{#if job.meta.statistics.info_count > 0}
				<span class="text-blue-600">{job.meta.statistics.info_count} info</span>
			{/if}
		</div>
	{/if}
{/if}

<!-- Self-Improve Dialog -->
<SelfImproveDialog
	suggestions={selfImproveSuggestions}
	bind:show={showSelfImproveDialog}
/>
