<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { v4 as uuidv4 } from 'uuid';

	import { getQCTemplateById, createQCTemplate, updateQCTemplate } from '$lib/apis/qc';
	import { getKnowledgeById } from '$lib/apis/knowledge';
	import { models } from '$lib/stores';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import KnowledgeSelector from '$lib/components/workspace/Models/Knowledge/KnowledgeSelector.svelte';

	const i18n = getContext('i18n');

	export let templateId: string | null = null;

	let loading = true;
	let saving = false;

	let name = '';
	let description = '';
	let system_prompt = '';
	let model_id = '';
	let meta: any = {
		knowledge_base_ids: [],
		checklist: [],
		vision_settings: { dpi: 300 },
		supported_file_types: ['pdf', 'png', 'jpg'],
		cross_reference_analysis: {
			enabled: false,
			categories: ['equipment_tags', 'wire_sizes', 'cross_sheet_refs', 'load_calcs']
		}
	};

	// Knowledge bases
	let selectedKnowledgeBases: Array<{ id: string; name: string }> = [];

	const resolveKnowledgeBases = async (ids: string[]) => {
		const resolved: Array<{ id: string; name: string }> = [];
		for (const id of ids) {
			try {
				const kb = await getKnowledgeById(localStorage.token, id);
				if (kb) {
					resolved.push({ id: kb.id, name: kb.name });
				}
			} catch {
				// KB may have been deleted
			}
		}
		selectedKnowledgeBases = resolved;
	};

	const addKnowledgeBase = (item: any) => {
		if (item.type !== 'collection') {
			toast.warning($i18n.t('Only knowledge base collections can be attached'));
			return;
		}
		if (meta.knowledge_base_ids.includes(item.id)) return;
		meta.knowledge_base_ids = [...meta.knowledge_base_ids, item.id];
		selectedKnowledgeBases = [...selectedKnowledgeBases, { id: item.id, name: item.name }];
	};

	const removeKnowledgeBase = (id: string) => {
		meta.knowledge_base_ids = meta.knowledge_base_ids.filter((kbId: string) => kbId !== id);
		selectedKnowledgeBases = selectedKnowledgeBases.filter((kb) => kb.id !== id);
	};

	// Checklist editing
	let newChecklistLabel = '';
	let newChecklistDescription = '';
	let newChecklistSeverity = 'minor';

	const addChecklistItem = () => {
		if (!newChecklistLabel.trim()) return;
		meta.checklist = [
			...meta.checklist,
			{
				id: uuidv4(),
				label: newChecklistLabel.trim(),
				description: newChecklistDescription.trim(),
				severity: newChecklistSeverity
			}
		];
		newChecklistLabel = '';
		newChecklistDescription = '';
		newChecklistSeverity = 'minor';
	};

	const removeChecklistItem = (id: string) => {
		meta.checklist = meta.checklist.filter((item: any) => item.id !== id);
	};

	const handleSave = async () => {
		if (!name.trim()) {
			toast.error($i18n.t('Name is required'));
			return;
		}
		saving = true;
		try {
			const data = {
				name: name.trim(),
				description: description.trim(),
				system_prompt,
				model_id: model_id || null,
				meta
			};

			if (templateId) {
				await updateQCTemplate(localStorage.token, templateId, data);
				toast.success($i18n.t('Template updated'));
			} else {
				const result = await createQCTemplate(localStorage.token, data);
				if (result) {
					toast.success($i18n.t('Template created'));
					goto(`/qc/templates/${result.id}`);
				}
			}
		} catch (e) {
			toast.error(`${e}`);
		}
		saving = false;
	};

	onMount(async () => {
		if (templateId) {
			try {
				const template = await getQCTemplateById(localStorage.token, templateId);
				if (template) {
					name = template.name;
					description = template.description || '';
					system_prompt = template.system_prompt || '';
					model_id = template.model_id || '';
					meta = {
						knowledge_base_ids: [],
						checklist: [],
						vision_settings: { dpi: 300 },
						supported_file_types: ['pdf', 'png', 'jpg'],
						cross_reference_analysis: {
							enabled: false,
							categories: ['equipment_tags', 'wire_sizes', 'cross_sheet_refs', 'load_calcs']
						},
						...(template.meta || {})
					};
					if (meta.knowledge_base_ids.length > 0) {
						await resolveKnowledgeBases(meta.knowledge_base_ids);
					}
				} else {
					toast.error($i18n.t('Template not found'));
					goto('/qc/templates');
				}
			} catch (e) {
				toast.error(`${e}`);
				goto('/qc/templates');
			}
		}
		loading = false;
	});
</script>

{#if loading}
	<div class="flex justify-center py-12">
		<Spinner className="size-5" />
	</div>
{:else}
	<div class="max-w-3xl mx-auto py-4">
		<div class="flex justify-between items-center mb-6">
			<button
				class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition flex items-center gap-1"
				on:click={() => goto('/qc/templates')}
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
				{$i18n.t('Back to Templates')}
			</button>
			<button
				class="px-4 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-xl disabled:opacity-50"
				disabled={saving}
				on:click={handleSave}
			>
				{saving ? $i18n.t('Saving...') : templateId ? $i18n.t('Save') : $i18n.t('Create')}
			</button>
		</div>

		<div class="space-y-5">
			<!-- Name -->
			<div>
				<label class="block text-sm font-medium mb-1" for="template-name">{$i18n.t('Name')}</label>
				<input
					id="template-name"
					type="text"
					bind:value={name}
					placeholder={$i18n.t('Template name...')}
					class="w-full text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none"
				/>
			</div>

			<!-- Description -->
			<div>
				<label class="block text-sm font-medium mb-1" for="template-desc"
					>{$i18n.t('Description')}</label
				>
				<input
					id="template-desc"
					type="text"
					bind:value={description}
					placeholder={$i18n.t('What does this template check for?')}
					class="w-full text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none"
				/>
			</div>

			<!-- Model -->
			<div>
				<label class="block text-sm font-medium mb-1" for="template-model"
					>{$i18n.t('Model')}</label
				>
				<select
					id="template-model"
					bind:value={model_id}
					class="w-full text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none"
				>
					<option value="">{$i18n.t('Select a model...')}</option>
					{#each $models as model}
						<option value={model.id}>{model.name || model.id}</option>
					{/each}
				</select>
			</div>

			<!-- System Prompt -->
			<div>
				<label class="block text-sm font-medium mb-1" for="template-prompt"
					>{$i18n.t('System Prompt')}</label
				>
				<p class="text-xs text-gray-500 mb-1">
					{$i18n.t('Custom instructions for the AI QC analyst. Will be appended to the default QC prompt.')}
				</p>
				<textarea
					id="template-prompt"
					bind:value={system_prompt}
					placeholder={$i18n.t('E.g., Focus on NEC code compliance, check wire sizing against load calculations...')}
					rows="8"
					class="w-full text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none font-mono"
				></textarea>
			</div>

			<!-- DPI Setting -->
			<div>
				<label class="block text-sm font-medium mb-1" for="template-dpi"
					>{$i18n.t('Render DPI')}</label
				>
				<select
					id="template-dpi"
					bind:value={meta.vision_settings.dpi}
					class="w-full max-w-xs text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none"
				>
					<option value={150}>150 DPI (Fast)</option>
					<option value={200}>200 DPI</option>
					<option value={300}>300 DPI (Recommended)</option>
					<option value={400}>400 DPI (High quality)</option>
				</select>
			</div>

			<!-- Knowledge Bases -->
			<div>
				<label class="block text-sm font-medium mb-1">{$i18n.t('Knowledge Bases')}</label>
				<p class="text-xs text-gray-500 mb-2">
					{$i18n.t('Attach standards documents or reference materials for the AI to reference')}
				</p>

				{#if selectedKnowledgeBases.length > 0}
					<div class="flex flex-wrap gap-2 mb-2">
						{#each selectedKnowledgeBases as kb}
							<span
								class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-sm bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
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
										d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
									/>
								</svg>
								{kb.name}
								<button
									class="ml-0.5 text-gray-400 hover:text-red-600 transition"
									on:click={() => removeKnowledgeBase(kb.id)}
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
											d="M6 18 18 6M6 6l12 12"
										/>
									</svg>
								</button>
							</span>
						{/each}
					</div>
				{/if}

				<KnowledgeSelector
					on:select={(e) => addKnowledgeBase(e.detail)}
				>
					<button
						type="button"
						class="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition flex items-center gap-1"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
						</svg>
						{$i18n.t('Add Knowledge Base')}
					</button>
				</KnowledgeSelector>
			</div>

			<!-- Checklist -->
			<div>
				<label class="block text-sm font-medium mb-2">{$i18n.t('Checklist Criteria')}</label>
				<p class="text-xs text-gray-500 mb-3">
					{$i18n.t('Define specific items the AI should check for on each page.')}
				</p>

				{#if meta.checklist.length > 0}
					<div class="space-y-2 mb-3">
						{#each meta.checklist as item}
							<div
								class="flex items-start gap-2 p-2 rounded-lg border border-gray-200 dark:border-gray-800"
							>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2">
										<span
											class="text-xs font-medium px-1.5 py-0.5 rounded uppercase {item.severity ===
											'critical'
												? 'bg-red-500/20 text-red-700 dark:text-red-200'
												: item.severity === 'major'
													? 'bg-orange-500/20 text-orange-700 dark:text-orange-200'
													: item.severity === 'minor'
														? 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-200'
														: 'bg-blue-500/20 text-blue-700 dark:text-blue-200'}"
										>
											{item.severity}
										</span>
										<span class="text-sm font-medium truncate">{item.label}</span>
									</div>
									{#if item.description}
										<p class="text-xs text-gray-500 mt-1">{item.description}</p>
									{/if}
								</div>
								<button
									class="p-1 text-gray-400 hover:text-red-600 transition shrink-0"
									on:click={() => removeChecklistItem(item.id)}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="size-4"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M6 18 18 6M6 6l12 12"
										/>
									</svg>
								</button>
							</div>
						{/each}
					</div>
				{/if}

				<div class="flex gap-2 items-end">
					<div class="flex-1">
						<input
							type="text"
							bind:value={newChecklistLabel}
							placeholder={$i18n.t('Checklist item label...')}
							class="w-full text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-1.5 outline-none"
							on:keydown={(e) => e.key === 'Enter' && addChecklistItem()}
						/>
					</div>
					<select
						bind:value={newChecklistSeverity}
						class="text-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
					>
						<option value="critical">Critical</option>
						<option value="major">Major</option>
						<option value="minor">Minor</option>
						<option value="info">Info</option>
					</select>
					<button
						class="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition"
						on:click={addChecklistItem}
					>
						{$i18n.t('Add')}
					</button>
				</div>
			</div>

			<!-- Cross-Reference Analysis -->
			<div>
				<div class="flex items-center justify-between mb-2">
					<div>
						<label class="block text-sm font-medium">{$i18n.t('Cross-Reference Analysis')}</label>
						<p class="text-xs text-gray-500 mt-0.5">
							{$i18n.t('Checks consistency across all pages after per-page analysis completes.')}
						</p>
					</div>
					<button
						type="button"
						class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out {meta.cross_reference_analysis.enabled ? 'bg-black dark:bg-white' : 'bg-gray-200 dark:bg-gray-700'}"
						role="switch"
						aria-checked={meta.cross_reference_analysis.enabled}
						on:click={() => { meta.cross_reference_analysis.enabled = !meta.cross_reference_analysis.enabled; meta = meta; }}
					>
						<span
							class="pointer-events-none inline-block h-5 w-5 transform rounded-full shadow ring-0 transition duration-200 ease-in-out {meta.cross_reference_analysis.enabled ? 'translate-x-5 bg-white dark:bg-black' : 'translate-x-0 bg-white dark:bg-gray-400'}"
						/>
					</button>
				</div>

				{#if meta.cross_reference_analysis.enabled}
					<div class="mt-3 p-3 rounded-xl border border-gray-200 dark:border-gray-800 space-y-2">
						<p class="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">
							{$i18n.t('Analysis categories:')}
						</p>

						<label class="flex items-center gap-2 text-sm cursor-pointer">
							<input
								type="checkbox"
								checked={meta.cross_reference_analysis.categories.includes('equipment_tags')}
								on:change={() => {
									const cats = meta.cross_reference_analysis.categories;
									if (cats.includes('equipment_tags')) {
										meta.cross_reference_analysis.categories = cats.filter((c) => c !== 'equipment_tags');
									} else {
										meta.cross_reference_analysis.categories = [...cats, 'equipment_tags'];
									}
									meta = meta;
								}}
								class="rounded"
							/>
							<span>{$i18n.t('Equipment tag consistency')}</span>
							<span class="text-xs text-gray-400">{$i18n.t('Same tag, same ratings everywhere')}</span>
						</label>

						<label class="flex items-center gap-2 text-sm cursor-pointer">
							<input
								type="checkbox"
								checked={meta.cross_reference_analysis.categories.includes('wire_sizes')}
								on:change={() => {
									const cats = meta.cross_reference_analysis.categories;
									if (cats.includes('wire_sizes')) {
										meta.cross_reference_analysis.categories = cats.filter((c) => c !== 'wire_sizes');
									} else {
										meta.cross_reference_analysis.categories = [...cats, 'wire_sizes'];
									}
									meta = meta;
								}}
								class="rounded"
							/>
							<span>{$i18n.t('Wire/cable sizing verification')}</span>
							<span class="text-xs text-gray-400">{$i18n.t('Schedule vs. plan wire sizes match')}</span>
						</label>

						<label class="flex items-center gap-2 text-sm cursor-pointer">
							<input
								type="checkbox"
								checked={meta.cross_reference_analysis.categories.includes('cross_sheet_refs')}
								on:change={() => {
									const cats = meta.cross_reference_analysis.categories;
									if (cats.includes('cross_sheet_refs')) {
										meta.cross_reference_analysis.categories = cats.filter((c) => c !== 'cross_sheet_refs');
									} else {
										meta.cross_reference_analysis.categories = [...cats, 'cross_sheet_refs'];
									}
									meta = meta;
								}}
								class="rounded"
							/>
							<span>{$i18n.t('Cross-sheet reference validation')}</span>
							<span class="text-xs text-gray-400">{$i18n.t('"See Detail A on E-501" resolves')}</span>
						</label>

						<label class="flex items-center gap-2 text-sm cursor-pointer">
							<input
								type="checkbox"
								checked={meta.cross_reference_analysis.categories.includes('load_calcs')}
								on:change={() => {
									const cats = meta.cross_reference_analysis.categories;
									if (cats.includes('load_calcs')) {
										meta.cross_reference_analysis.categories = cats.filter((c) => c !== 'load_calcs');
									} else {
										meta.cross_reference_analysis.categories = [...cats, 'load_calcs'];
									}
									meta = meta;
								}}
								class="rounded"
							/>
							<span>{$i18n.t('Load calculation consistency')}</span>
							<span class="text-xs text-gray-400">{$i18n.t('Ratings, loads, and feeder sizing')}</span>
						</label>

						<p class="text-xs text-gray-400 mt-2 pt-2 border-t border-gray-200 dark:border-gray-800">
							{$i18n.t('Adds ~40-60% more analysis time. Uses text extraction + AI correlation across all pages.')}
						</p>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
