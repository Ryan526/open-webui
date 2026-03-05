<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { getQCTemplates, createQCJob, addQCJobDocument } from '$lib/apis/qc';
	import { models } from '$lib/stores';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let templates: any[] = [];
	let loading = true;
	let creating = false;
	let uploading = false;

	let name = '';
	let selectedTemplateId = '';
	let selectedModelId = '';
	let files: FileList | null = null;
	let uploadedFiles: { name: string; type: string }[] = [];

	let fileInput: HTMLInputElement;

	$: selectedTemplate = templates.find((t) => t.id === selectedTemplateId);

	$: if (selectedTemplate) {
		if (selectedTemplate.model_id && !selectedModelId) {
			selectedModelId = selectedTemplate.model_id;
		}
	}

	const handleCreate = async () => {
		if (!name.trim()) {
			toast.error($i18n.t('Job name is required'));
			return;
		}
		if (!selectedModelId) {
			toast.error($i18n.t('Please select a model'));
			return;
		}

		creating = true;
		try {
			const job = await createQCJob(localStorage.token, {
				name: name.trim(),
				template_id: selectedTemplateId || undefined,
				model_id: selectedModelId
			});

			if (job) {
				// Upload documents
				if (files && files.length > 0) {
					uploading = true;
					for (const file of Array.from(files)) {
						try {
							await addQCJobDocument(localStorage.token, job.id, file, 'subject');
						} catch (e) {
							toast.error(`Failed to upload ${file.name}: ${e}`);
						}
					}
					uploading = false;
				}

				toast.success($i18n.t('QC Job created'));
				goto(`/qc/jobs/${job.id}`);
			}
		} catch (e) {
			toast.error(`${e}`);
		}
		creating = false;
	};

	const handleFileSelect = () => {
		if (files) {
			uploadedFiles = Array.from(files).map((f) => ({ name: f.name, type: f.type }));
		}
	};

	onMount(async () => {
		try {
			templates = (await getQCTemplates(localStorage.token)) || [];
		} catch (e) {
			toast.error(`${e}`);
		}
		loading = false;
	});
</script>

{#if loading}
	<div class="flex justify-center py-12">
		<Spinner className="size-5" />
	</div>
{:else}
	<div class="max-w-2xl mx-auto py-4">
		<div class="flex justify-between items-center mb-6">
			<button
				class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition flex items-center gap-1"
				on:click={() => goto('/qc/jobs')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="size-4"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
				</svg>
				{$i18n.t('Back to Jobs')}
			</button>
		</div>

		<h2 class="text-lg font-medium mb-4">{$i18n.t('Create QC Job')}</h2>

		<div class="space-y-5">
			<!-- Job Name -->
			<div>
				<label class="block text-sm font-medium mb-1" for="job-name">{$i18n.t('Job Name')}</label>
				<input
					id="job-name"
					type="text"
					bind:value={name}
					placeholder={$i18n.t('E.g., Panel Schedule Review - Building A')}
					class="w-full text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none"
				/>
			</div>

			<!-- Template Selection -->
			<div>
				<label class="block text-sm font-medium mb-1" for="job-template"
					>{$i18n.t('Template (Optional)')}</label
				>
				<select
					id="job-template"
					bind:value={selectedTemplateId}
					class="w-full text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none"
				>
					<option value="">{$i18n.t('No template - configure manually')}</option>
					{#each templates as template}
						<option value={template.id}>{template.name}</option>
					{/each}
				</select>
				{#if selectedTemplate?.description}
					<p class="text-xs text-gray-500 mt-1">{selectedTemplate.description}</p>
				{/if}
			</div>

			<!-- Model Selection -->
			<div>
				<label class="block text-sm font-medium mb-1" for="job-model">{$i18n.t('Model')}</label>
				<select
					id="job-model"
					bind:value={selectedModelId}
					class="w-full text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none"
				>
					<option value="">{$i18n.t('Select a vision model...')}</option>
					{#each $models as model}
						<option value={model.id}>{model.name || model.id}</option>
					{/each}
				</select>
			</div>

			<!-- Document Upload -->
			<div>
				<label class="block text-sm font-medium mb-1">{$i18n.t('Documents')}</label>
				<p class="text-xs text-gray-500 mb-2">
					{$i18n.t('Upload PDF files or images for QC review. You can also add more documents later.')}
				</p>

				<div
					class="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-xl p-6 text-center cursor-pointer hover:border-gray-400 dark:hover:border-gray-600 transition"
					on:click={() => fileInput?.click()}
					on:keydown={(e) => e.key === 'Enter' && fileInput?.click()}
					role="button"
					tabindex="0"
				>
					<input
						bind:this={fileInput}
						bind:files
						type="file"
						multiple
						accept=".pdf,.png,.jpg,.jpeg,.tiff,.xlsx,.docx"
						class="hidden"
						on:change={handleFileSelect}
					/>

					{#if uploadedFiles.length > 0}
						<div class="space-y-1">
							{#each uploadedFiles as file}
								<div class="text-sm text-gray-700 dark:text-gray-300">{file.name}</div>
							{/each}
						</div>
					{:else}
						<div class="text-gray-400">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-8 mx-auto mb-2"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z"
								/>
							</svg>
							<p class="text-sm">{$i18n.t('Click to upload or drag and drop')}</p>
							<p class="text-xs mt-1">PDF, PNG, JPG, XLSX, DOCX</p>
						</div>
					{/if}
				</div>
			</div>

			<!-- Create Button -->
			<div class="flex justify-end">
				<button
					class="px-5 py-2.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-xl disabled:opacity-50"
					disabled={creating || uploading}
					on:click={handleCreate}
				>
					{#if creating || uploading}
						<div class="flex items-center gap-2">
							<Spinner className="size-4" />
							{uploading ? $i18n.t('Uploading documents...') : $i18n.t('Creating...')}
						</div>
					{:else}
						{$i18n.t('Create Job')}
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}
