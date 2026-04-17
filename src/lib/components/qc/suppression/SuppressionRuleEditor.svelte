<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, createEventDispatcher } from 'svelte';

	import { createQCSuppressionRule, updateQCSuppressionRule } from '$lib/apis/qc';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let rule: any | null = null;
	export let show: boolean = false;
	export let templateChoices: { id: string; name: string }[] = [];
	export let projectChoices: { id: string; name: string }[] = [];

	let form = {
		scope: 'global' as 'global' | 'template' | 'project',
		template_id: '',
		project_id: '',
		name: '',
		enabled: 1,
		match_type: 'title_contains' as 'title_exact' | 'title_regex' | 'title_contains' | 'checklist_item',
		match_value: '',
		severity_filter: '',
		page_tag_filter: '',
		reason: ''
	};

	$: if (show) {
		if (rule) {
			form = {
				scope: rule.scope,
				template_id: rule.template_id || '',
				project_id: rule.project_id || '',
				name: rule.name,
				enabled: rule.enabled ?? 1,
				match_type: rule.match_type,
				match_value: rule.match_value,
				severity_filter: rule.severity_filter || '',
				page_tag_filter: rule.page_tag_filter || '',
				reason: rule.reason || ''
			};
		} else {
			form = {
				scope: 'global',
				template_id: '',
				project_id: '',
				name: '',
				enabled: 1,
				match_type: 'title_contains',
				match_value: '',
				severity_filter: '',
				page_tag_filter: '',
				reason: ''
			};
		}
	}

	let saving = false;

	const save = async () => {
		if (!form.name.trim()) {
			toast.error($i18n.t('Name is required'));
			return;
		}
		if (!form.match_value.trim()) {
			toast.error($i18n.t('Match value is required'));
			return;
		}
		saving = true;
		try {
			const payload: any = {
				scope: form.scope,
				name: form.name.trim(),
				enabled: form.enabled,
				match_type: form.match_type,
				match_value: form.match_value.trim(),
				severity_filter: form.severity_filter || null,
				page_tag_filter: form.page_tag_filter || null,
				reason: form.reason.trim() || null,
				template_id: form.scope === 'template' ? form.template_id || null : null,
				project_id: form.scope === 'project' ? form.project_id || null : null
			};
			if (rule?.id) {
				await updateQCSuppressionRule(localStorage.token, rule.id, payload);
				toast.success($i18n.t('Rule updated'));
			} else {
				await createQCSuppressionRule(localStorage.token, payload);
				toast.success($i18n.t('Rule created'));
			}
			dispatch('saved');
			show = false;
		} catch (e) {
			toast.error(`${e}`);
		}
		saving = false;
	};
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
			class="w-[min(540px,calc(100vw-2rem))] max-h-[85vh] overflow-y-auto bg-white dark:bg-gray-900 rounded-2xl shadow-xl"
			on:click|stopPropagation
			role="dialog"
		>
			<div class="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
				<h3 class="text-sm font-medium">{rule ? $i18n.t('Edit Suppression Rule') : $i18n.t('New Suppression Rule')}</h3>
				<button class="text-xs text-gray-500 hover:text-gray-700" on:click={() => (show = false)}>✕</button>
			</div>
			<div class="p-4 space-y-3">
				<div>
					<label class="block text-xs text-gray-500 mb-1" for="rule-name">{$i18n.t('Name')}</label>
					<input
						id="rule-name"
						type="text"
						bind:value={form.name}
						class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
					/>
				</div>
				<div class="grid grid-cols-2 gap-3">
					<div>
						<label class="block text-xs text-gray-500 mb-1" for="rule-scope">{$i18n.t('Scope')}</label>
						<select
							id="rule-scope"
							bind:value={form.scope}
							class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
						>
							<option value="global">{$i18n.t('Global')}</option>
							<option value="template">{$i18n.t('Template')}</option>
							<option value="project">{$i18n.t('Project')}</option>
						</select>
					</div>
					<div>
						<label class="block text-xs text-gray-500 mb-1" for="rule-match-type">{$i18n.t('Match type')}</label>
						<select
							id="rule-match-type"
							bind:value={form.match_type}
							class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
						>
							<option value="title_contains">{$i18n.t('Title contains')}</option>
							<option value="title_exact">{$i18n.t('Title exact')}</option>
							<option value="title_regex">{$i18n.t('Title regex')}</option>
							<option value="checklist_item">{$i18n.t('Checklist item')}</option>
						</select>
					</div>
				</div>

				{#if form.scope === 'template'}
					<div>
						<label class="block text-xs text-gray-500 mb-1" for="rule-template-id">{$i18n.t('Template')}</label>
						<select
							id="rule-template-id"
							bind:value={form.template_id}
							class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
						>
							<option value="">{$i18n.t('Select...')}</option>
							{#each templateChoices as t}
								<option value={t.id}>{t.name}</option>
							{/each}
						</select>
					</div>
				{:else if form.scope === 'project'}
					<div>
						<label class="block text-xs text-gray-500 mb-1" for="rule-project-id">{$i18n.t('Project')}</label>
						<select
							id="rule-project-id"
							bind:value={form.project_id}
							class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
						>
							<option value="">{$i18n.t('Select...')}</option>
							{#each projectChoices as p}
								<option value={p.id}>{p.name}</option>
							{/each}
						</select>
					</div>
				{/if}

				<div>
					<label class="block text-xs text-gray-500 mb-1" for="rule-match-value">{$i18n.t('Match value')}</label>
					<input
						id="rule-match-value"
						type="text"
						bind:value={form.match_value}
						placeholder={form.match_type === 'checklist_item' ? $i18n.t('Checklist item ID') : $i18n.t('Text or regex pattern')}
						class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
					/>
				</div>

				<div class="grid grid-cols-2 gap-3">
					<div>
						<label class="block text-xs text-gray-500 mb-1" for="rule-severity-cap">{$i18n.t('Severity cap (optional)')}</label>
						<select
							id="rule-severity-cap"
							bind:value={form.severity_filter}
							class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
						>
							<option value="">{$i18n.t('Any')}</option>
							<option value="info">{$i18n.t('Only info')}</option>
							<option value="minor">{$i18n.t('Minor and below')}</option>
							<option value="major">{$i18n.t('Major and below')}</option>
							<option value="critical">{$i18n.t('All (incl. critical)')}</option>
						</select>
					</div>
					<div>
						<label class="block text-xs text-gray-500 mb-1" for="rule-page-tag">{$i18n.t('Page tag filter (optional)')}</label>
						<input
							id="rule-page-tag"
							type="text"
							bind:value={form.page_tag_filter}
							placeholder={$i18n.t('E.g. schedule, detail')}
							class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
						/>
					</div>
				</div>

				<div>
					<label class="block text-xs text-gray-500 mb-1" for="rule-reason">{$i18n.t('Reason (optional)')}</label>
					<textarea
						id="rule-reason"
						bind:value={form.reason}
						rows="2"
						placeholder={$i18n.t('Why is this suppressed?')}
						class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
					></textarea>
				</div>

				<label class="flex items-center gap-2 text-xs text-gray-600">
					<input
						type="checkbox"
						checked={form.enabled === 1}
						on:change={(e) => (form.enabled = (e.target as HTMLInputElement).checked ? 1 : 0)}
					/>
					{$i18n.t('Enabled')}
				</label>

				<div class="flex justify-end gap-2 pt-2">
					<button
						class="px-3 py-1.5 text-sm rounded-xl border border-gray-200 dark:border-gray-800"
						on:click={() => (show = false)}
						disabled={saving}
					>
						{$i18n.t('Cancel')}
					</button>
					<button
						class="px-3 py-1.5 text-sm font-medium bg-black text-white dark:bg-white dark:text-black rounded-xl disabled:opacity-50"
						on:click={save}
						disabled={saving}
					>
						{saving ? $i18n.t('Saving...') : $i18n.t('Save')}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
