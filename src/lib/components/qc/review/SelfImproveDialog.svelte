<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, createEventDispatcher } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';

	import { getQCTemplateById, updateQCTemplate } from '$lib/apis/qc';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let suggestions: any;
	export let show = false;

	let applying = false;

	// Track which suggestions are selected (default all checked)
	let promptSelections: boolean[] = [];
	let checklistSelections: boolean[] = [];

	$: if (suggestions) {
		promptSelections = (suggestions.system_prompt_changes || []).map(() => true);
		checklistSelections = (suggestions.checklist_changes || []).map(() => true);
	}

	$: isStale =
		suggestions?.template_updated_at &&
		suggestions?.job_created_at &&
		suggestions.template_updated_at > suggestions.job_created_at;

	const applyChanges = async () => {
		if (!suggestions?.template_id) return;
		applying = true;

		try {
			// Fetch current template
			const template = await getQCTemplateById(localStorage.token, suggestions.template_id);
			if (!template) {
				toast.error($i18n.t('Template not found'));
				return;
			}

			let systemPrompt = template.system_prompt || '';
			let meta = { ...(template.meta || {}) };
			let checklist = [...(meta.checklist || [])];

			// Apply selected system prompt changes
			const promptChanges = suggestions.system_prompt_changes || [];
			for (let i = 0; i < promptChanges.length; i++) {
				if (!promptSelections[i]) continue;
				const change = promptChanges[i];

				if (change.action === 'append') {
					systemPrompt = systemPrompt.trimEnd() + '\n\n' + change.text;
				} else if (change.action === 'replace' && change.original) {
					systemPrompt = systemPrompt.replace(change.original, change.replacement || '');
				} else if (change.action === 'remove' && change.text) {
					systemPrompt = systemPrompt.replace(change.text, '');
				}
			}

			// Apply selected checklist changes
			const clChanges = suggestions.checklist_changes || [];
			for (let i = 0; i < clChanges.length; i++) {
				if (!checklistSelections[i]) continue;
				const change = clChanges[i];

				if (change.action === 'add' && change.item) {
					checklist.push({
						id: uuidv4(),
						label: change.item.label || '',
						description: change.item.description || '',
						severity: change.item.severity || 'info'
					});
				} else if (change.action === 'modify' && change.item_id && change.updates) {
					const idx = checklist.findIndex((c) => c.id === change.item_id);
					if (idx !== -1) {
						checklist[idx] = { ...checklist[idx], ...change.updates };
					}
				} else if (change.action === 'remove' && change.item_id) {
					checklist = checklist.filter((c) => c.id !== change.item_id);
				}
			}

			meta.checklist = checklist;

			// Update template
			await updateQCTemplate(localStorage.token, suggestions.template_id, {
				name: template.name,
				description: template.description,
				system_prompt: systemPrompt.trim(),
				model_id: template.model_id,
				meta
			});

			toast.success($i18n.t('Template updated successfully'));
			show = false;
			dispatch('applied');
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			applying = false;
		}
	};

	const close = () => {
		show = false;
		dispatch('close');
	};
</script>

{#if show && suggestions}
	<!-- Backdrop -->
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" on:click|self={close}>
		<div
			class="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col mx-4"
		>
			<!-- Header -->
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
				<h2 class="text-base font-semibold">{$i18n.t('Template Improvement Suggestions')}</h2>
				{#if suggestions.summary}
					<p class="text-xs text-gray-500 mt-1">{suggestions.summary}</p>
				{/if}
			</div>

			<!-- Scrollable content -->
			<div class="flex-1 overflow-y-auto px-6 py-4 space-y-6">
				<!-- Staleness warning -->
				{#if isStale}
					<div
						class="flex items-center gap-2 p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 text-xs text-yellow-700 dark:text-yellow-400"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4 shrink-0"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
							/>
						</svg>
						{$i18n.t('The template has been modified since this job was created. Review suggestions carefully.')}
					</div>
				{/if}

				<!-- Error state -->
				{#if suggestions.error}
					<div
						class="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-xs text-red-600 dark:text-red-400"
					>
						{suggestions.summary}
						{#if suggestions.raw_response}
							<pre class="mt-2 whitespace-pre-wrap text-gray-500">{suggestions.raw_response}</pre>
						{/if}
					</div>
				{/if}

				<!-- System Prompt Changes -->
				{#if (suggestions.system_prompt_changes || []).length > 0}
					<div>
						<h3 class="text-sm font-medium mb-2">{$i18n.t('System Prompt Changes')}</h3>
						<div class="space-y-2">
							{#each suggestions.system_prompt_changes as change, i}
								<div class="flex items-start gap-2 p-3 rounded-lg border border-gray-200 dark:border-gray-800">
									<input
										type="checkbox"
										bind:checked={promptSelections[i]}
										class="mt-0.5 shrink-0"
									/>
									<div class="flex-1 min-w-0">
										<div class="flex items-center gap-2 mb-1">
											<span
												class="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded {change.action ===
												'append'
													? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
													: change.action === 'replace'
														? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
														: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}"
											>
												{change.action}
											</span>
										</div>

										{#if change.action === 'replace'}
											<div class="text-xs space-y-1">
												<div class="p-1.5 rounded bg-red-50 dark:bg-red-900/10 line-through text-red-600 dark:text-red-400 whitespace-pre-wrap">
													{change.original}
												</div>
												<div class="p-1.5 rounded bg-green-50 dark:bg-green-900/10 text-green-600 dark:text-green-400 whitespace-pre-wrap">
													{change.replacement}
												</div>
											</div>
										{:else if change.action === 'append'}
											<div class="text-xs p-1.5 rounded bg-green-50 dark:bg-green-900/10 text-green-600 dark:text-green-400 whitespace-pre-wrap">
												{change.text}
											</div>
										{:else if change.action === 'remove'}
											<div class="text-xs p-1.5 rounded bg-red-50 dark:bg-red-900/10 line-through text-red-600 dark:text-red-400 whitespace-pre-wrap">
												{change.text}
											</div>
										{/if}

										{#if change.reason}
											<p class="text-xs text-gray-400 mt-1.5 italic">{change.reason}</p>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Checklist Changes -->
				{#if (suggestions.checklist_changes || []).length > 0}
					<div>
						<h3 class="text-sm font-medium mb-2">{$i18n.t('Checklist Changes')}</h3>
						<div class="space-y-2">
							{#each suggestions.checklist_changes as change, i}
								<div class="flex items-start gap-2 p-3 rounded-lg border border-gray-200 dark:border-gray-800">
									<input
										type="checkbox"
										bind:checked={checklistSelections[i]}
										class="mt-0.5 shrink-0"
									/>
									<div class="flex-1 min-w-0">
										<div class="flex items-center gap-2 mb-1">
											<span
												class="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded {change.action ===
												'add'
													? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
													: change.action === 'modify'
														? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
														: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}"
											>
												{change.action}
											</span>
										</div>

										{#if change.action === 'add' && change.item}
											<div class="text-xs p-1.5 rounded bg-green-50 dark:bg-green-900/10 text-green-600 dark:text-green-400">
												<span class="font-medium">{change.item.label}</span>
												{#if change.item.severity}
													<span class="ml-1 text-[10px] uppercase opacity-75">({change.item.severity})</span>
												{/if}
												{#if change.item.description}
													<p class="mt-0.5 opacity-80">{change.item.description}</p>
												{/if}
											</div>
										{:else if change.action === 'modify' && change.updates}
											<div class="text-xs p-1.5 rounded bg-blue-50 dark:bg-blue-900/10 text-blue-600 dark:text-blue-400">
												<span class="font-medium">Update item:</span>
												{#if change.updates.label}
													<p>Label: {change.updates.label}</p>
												{/if}
												{#if change.updates.description}
													<p>Description: {change.updates.description}</p>
												{/if}
												{#if change.updates.severity}
													<p>Severity: {change.updates.severity}</p>
												{/if}
											</div>
										{:else if change.action === 'remove'}
											<div class="text-xs p-1.5 rounded bg-red-50 dark:bg-red-900/10 line-through text-red-600 dark:text-red-400">
												Remove item: {change.item_id}
											</div>
										{/if}

										{#if change.reason}
											<p class="text-xs text-gray-400 mt-1.5 italic">{change.reason}</p>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- No suggestions -->
				{#if !suggestions.error && (suggestions.system_prompt_changes || []).length === 0 && (suggestions.checklist_changes || []).length === 0}
					<div class="text-center text-gray-400 py-8 text-sm">
						{$i18n.t('No changes suggested based on the review feedback.')}
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="px-6 py-3 border-t border-gray-200 dark:border-gray-800 flex items-center justify-end gap-2">
				<button
					class="px-4 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
					on:click={close}
				>
					{$i18n.t('Cancel')}
				</button>
				{#if !suggestions.error && ((suggestions.system_prompt_changes || []).length > 0 || (suggestions.checklist_changes || []).length > 0)}
					<button
						class="px-4 py-1.5 text-xs font-medium bg-black text-white dark:bg-white dark:text-black rounded-lg hover:opacity-90 transition disabled:opacity-50"
						disabled={applying ||
							(!promptSelections.some(Boolean) && !checklistSelections.some(Boolean))}
						on:click={applyChanges}
					>
						{applying ? $i18n.t('Applying...') : $i18n.t('Apply Selected Changes')}
					</button>
				{/if}
			</div>
		</div>
	</div>
{/if}
