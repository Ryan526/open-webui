<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import {
		getQCTestSet,
		updateQCTestSet,
		addQCTestSetDocument,
		removeQCTestSetDocument,
		deleteQCTestSetExpectedFinding,
		seedTestSetFromJob,
		getQCJobs
	} from '$lib/apis/qc';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import SeverityBadge from '../SeverityBadge.svelte';
	import ExpectedFindingEditor from './ExpectedFindingEditor.svelte';
	import RunTestDialog from './RunTestDialog.svelte';

	const i18n = getContext('i18n');

	export let testSetId: string;

	let loading = true;
	let ts: any = null;
	let documents: any[] = [];
	let expected: any[] = [];

	let name = '';
	let description = '';

	let fileInput: HTMLInputElement;

	let showEfEditor = false;
	let editingEf: any | null = null;

	let showRunDialog = false;

	let seedJobId = '';
	let jobs: any[] = [];
	let seeding = false;

	const load = async () => {
		loading = true;
		try {
			const res = await getQCTestSet(localStorage.token, testSetId);
			if (!res) {
				toast.error($i18n.t('Test set not found'));
				goto('/qc/test-sets');
				return;
			}
			ts = res;
			documents = res.documents || [];
			expected = res.expected_findings || [];
			name = res.name;
			description = res.description || '';
			jobs = (await getQCJobs(localStorage.token)) || [];
		} catch (e) {
			toast.error(`${e}`);
		}
		loading = false;
	};

	const saveMeta = async () => {
		try {
			await updateQCTestSet(localStorage.token, testSetId, {
				name: name.trim(),
				description: description.trim() || undefined
			});
			toast.success($i18n.t('Saved'));
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const handleUpload = async (event: Event) => {
		const input = event.target as HTMLInputElement;
		if (!input.files) return;
		for (const file of Array.from(input.files)) {
			try {
				await addQCTestSetDocument(localStorage.token, testSetId, file);
				toast.success(`${file.name} uploaded`);
			} catch (e) {
				toast.error(`${file.name}: ${e}`);
			}
		}
		input.value = '';
		await load();
	};

	const removeDoc = async (docId: string) => {
		if (!confirm($i18n.t('Remove this document and its expected findings?'))) return;
		try {
			await removeQCTestSetDocument(localStorage.token, testSetId, docId);
			await load();
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const newExpected = () => {
		editingEf = null;
		showEfEditor = true;
	};

	const editExpected = (ef: any) => {
		editingEf = ef;
		showEfEditor = true;
	};

	const removeExpected = async (efId: string) => {
		if (!confirm($i18n.t('Delete this expected finding?'))) return;
		try {
			await deleteQCTestSetExpectedFinding(localStorage.token, testSetId, efId);
			await load();
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const runSeed = async () => {
		if (!seedJobId) return;
		seeding = true;
		try {
			const res = await seedTestSetFromJob(localStorage.token, testSetId, seedJobId);
			toast.success($i18n.t('Seeded {{n}} expected finding(s)', { n: res?.seeded ?? 0 }));
			await load();
		} catch (e) {
			toast.error(`${e}`);
		}
		seeding = false;
	};

	onMount(load);
</script>

{#if loading}
	<div class="flex justify-center py-12"><Spinner className="size-5" /></div>
{:else if ts}
	<div class="py-3">
		<button
			class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition mb-4"
			on:click={() => goto('/qc/test-sets')}
		>
			← {$i18n.t('Back to Test Sets')}
		</button>

		<div class="space-y-3 mb-6">
			<input
				type="text"
				bind:value={name}
				class="w-full text-lg font-medium rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none"
			/>
			<textarea
				bind:value={description}
				rows="2"
				placeholder={$i18n.t('Description')}
				class="w-full text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none"
			/>
			<div class="flex justify-end gap-2">
				<button class="px-3 py-1 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800" on:click={saveMeta}>
					{$i18n.t('Save')}
				</button>
				<button class="px-3 py-1 text-xs rounded-lg border border-blue-300 dark:border-blue-700 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30" on:click={() => (showRunDialog = true)}>
					{$i18n.t('Run Test Set')}
				</button>
			</div>
		</div>

		<!-- Documents -->
		<div class="mb-6">
			<div class="flex items-center justify-between mb-2">
				<h3 class="text-sm font-medium">{$i18n.t('Documents')} ({documents.length})</h3>
				<label class="px-2 py-1 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer">
					+ {$i18n.t('Upload')}
					<input
						bind:this={fileInput}
						type="file"
						multiple
						accept=".pdf,.png,.jpg,.jpeg,.tiff,.xlsx,.docx"
						class="hidden"
						on:change={handleUpload}
					/>
				</label>
			</div>
			{#if documents.length === 0}
				<div class="text-xs text-gray-400 py-2">{$i18n.t('Upload PDFs or images to define test inputs.')}</div>
			{:else}
				<div class="space-y-1">
					{#each documents as d}
						<div class="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-800 text-xs">
							<span class="flex-1 truncate">{d.name || d.id}</span>
							<span class="text-gray-500">{d.page_count ?? '?'} pp</span>
							<button class="text-red-500 hover:underline" on:click={() => removeDoc(d.id)}>{$i18n.t('Remove')}</button>
						</div>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Seed from job -->
		<div class="mb-6 rounded-xl border border-gray-200 dark:border-gray-800 p-3">
			<h4 class="text-xs font-medium mb-2">{$i18n.t('Seed expected findings from a job')}</h4>
			<div class="flex items-center gap-2 text-xs">
				<select
					bind:value={seedJobId}
					class="flex-1 rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
				>
					<option value="">{$i18n.t('Select a completed job...')}</option>
					{#each jobs as j}
						<option value={j.id}>{j.name}</option>
					{/each}
				</select>
				<button
					class="px-3 py-1.5 rounded-lg bg-black text-white dark:bg-white dark:text-black disabled:opacity-50"
					on:click={runSeed}
					disabled={!seedJobId || seeding}
				>
					{seeding ? $i18n.t('Seeding...') : $i18n.t('Seed')}
				</button>
			</div>
			<p class="text-[10px] text-gray-500 mt-1.5">{$i18n.t('Only confirmed findings whose file is present in this test set are copied.')}</p>
		</div>

		<!-- Expected findings -->
		<div>
			<div class="flex items-center justify-between mb-2">
				<h3 class="text-sm font-medium">{$i18n.t('Expected Findings')} ({expected.length})</h3>
				<button
					class="px-2 py-1 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50"
					on:click={newExpected}
					disabled={documents.length === 0}
				>
					+ {$i18n.t('Add expected finding')}
				</button>
			</div>
			{#if expected.length === 0}
				<div class="text-xs text-gray-400 py-2">{$i18n.t('No expected findings yet.')}</div>
			{:else}
				<div class="space-y-1">
					{#each expected as ef}
						<div class="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-800 text-xs">
							<SeverityBadge severity={ef.severity} />
							<span class="flex-1 truncate">{ef.title}</span>
							<span class="text-gray-500">p.{ef.page_number ?? '?'}</span>
							{#if ef.seeded_from_finding_id}
								<span class="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-600">seeded</span>
							{/if}
							<button class="text-blue-600 hover:underline" on:click={() => editExpected(ef)}>{$i18n.t('Edit')}</button>
							<button class="text-red-500 hover:underline" on:click={() => removeExpected(ef.id)}>{$i18n.t('Delete')}</button>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>

	<ExpectedFindingEditor
		{testSetId}
		{documents}
		existing={editingEf}
		bind:show={showEfEditor}
		on:saved={load}
	/>

	<RunTestDialog {testSetId} bind:show={showRunDialog} />
{/if}
