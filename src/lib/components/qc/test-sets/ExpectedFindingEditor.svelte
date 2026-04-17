<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, createEventDispatcher } from 'svelte';

	import {
		createQCTestSetExpectedFinding,
		updateQCTestSetExpectedFinding
	} from '$lib/apis/qc';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let testSetId: string;
	export let documents: { id: string; name?: string | null; page_count?: number | null }[] = [];
	export let existing: any | null = null;
	export let show: boolean = false;

	let form = {
		document_id: '',
		page_number: 1,
		checklist_item_id: '',
		severity: 'minor' as 'critical' | 'major' | 'minor' | 'info',
		title: '',
		description: '',
		location_json: '',
		match_patterns_raw: ''
	};

	let saving = false;

	$: if (show) {
		if (existing) {
			form = {
				document_id: existing.document_id,
				page_number: existing.page_number ?? 1,
				checklist_item_id: existing.checklist_item_id || '',
				severity: existing.severity || 'minor',
				title: existing.title || '',
				description: existing.description || '',
				location_json: existing.location ? JSON.stringify(existing.location) : '',
				match_patterns_raw: Array.isArray(existing.match_title_patterns)
					? existing.match_title_patterns.join('\n')
					: ''
			};
		} else {
			form = {
				document_id: documents[0]?.id || '',
				page_number: 1,
				checklist_item_id: '',
				severity: 'minor',
				title: '',
				description: '',
				location_json: '',
				match_patterns_raw: ''
			};
		}
	}

	const save = async () => {
		if (!form.document_id) {
			toast.error($i18n.t('Document is required'));
			return;
		}
		if (!form.title.trim()) {
			toast.error($i18n.t('Title is required'));
			return;
		}
		let location: object | undefined = undefined;
		if (form.location_json.trim()) {
			try {
				location = JSON.parse(form.location_json);
			} catch {
				toast.error($i18n.t('Location must be valid JSON'));
				return;
			}
		}
		const patterns = form.match_patterns_raw
			.split(/\r?\n/)
			.map((x) => x.trim())
			.filter(Boolean);

		const payload = {
			document_id: form.document_id,
			page_number: form.page_number || undefined,
			checklist_item_id: form.checklist_item_id.trim() || undefined,
			severity: form.severity,
			title: form.title.trim(),
			description: form.description.trim() || undefined,
			location,
			match_title_patterns: patterns.length ? patterns : undefined
		};

		saving = true;
		try {
			if (existing?.id) {
				await updateQCTestSetExpectedFinding(localStorage.token, testSetId, existing.id, payload);
			} else {
				await createQCTestSetExpectedFinding(localStorage.token, testSetId, payload);
			}
			toast.success($i18n.t('Saved'));
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
			class="w-[min(560px,calc(100vw-2rem))] max-h-[85vh] overflow-y-auto bg-white dark:bg-gray-900 rounded-2xl shadow-xl"
			on:click|stopPropagation
			role="dialog"
		>
			<div class="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
				<h3 class="text-sm font-medium">
					{existing ? $i18n.t('Edit Expected Finding') : $i18n.t('New Expected Finding')}
				</h3>
				<button class="text-xs text-gray-500 hover:text-gray-700" on:click={() => (show = false)}>✕</button>
			</div>
			<div class="p-4 space-y-3">
				<div>
					<label class="block text-xs text-gray-500 mb-1" for="ef-doc">{$i18n.t('Document')}</label>
					<select
						id="ef-doc"
						bind:value={form.document_id}
						class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
					>
						{#each documents as d}
							<option value={d.id}>{d.name || d.id} ({d.page_count ?? '?'} p)</option>
						{/each}
					</select>
				</div>
				<div class="grid grid-cols-2 gap-3">
					<div>
						<label class="block text-xs text-gray-500 mb-1" for="ef-page">{$i18n.t('Page')}</label>
						<input
							id="ef-page"
							type="number"
							min="1"
							bind:value={form.page_number}
							class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
						/>
					</div>
					<div>
						<label class="block text-xs text-gray-500 mb-1" for="ef-sev">{$i18n.t('Severity')}</label>
						<select
							id="ef-sev"
							bind:value={form.severity}
							class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
						>
							<option value="critical">{$i18n.t('Critical')}</option>
							<option value="major">{$i18n.t('Major')}</option>
							<option value="minor">{$i18n.t('Minor')}</option>
							<option value="info">{$i18n.t('Info')}</option>
						</select>
					</div>
				</div>
				<div>
					<label class="block text-xs text-gray-500 mb-1" for="ef-title">{$i18n.t('Title')}</label>
					<input
						id="ef-title"
						type="text"
						bind:value={form.title}
						class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
					/>
				</div>
				<div>
					<label class="block text-xs text-gray-500 mb-1" for="ef-desc">{$i18n.t('Description')}</label>
					<textarea
						id="ef-desc"
						bind:value={form.description}
						rows="2"
						class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
					/>
				</div>
				<div>
					<label class="block text-xs text-gray-500 mb-1" for="ef-checklist">{$i18n.t('Checklist item id (optional)')}</label>
					<input
						id="ef-checklist"
						type="text"
						bind:value={form.checklist_item_id}
						class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none"
					/>
				</div>
				<div>
					<label class="block text-xs text-gray-500 mb-1" for="ef-loc">{$i18n.t('Location JSON (optional)')}</label>
					<input
						id="ef-loc"
						type="text"
						placeholder={'{"x":0.2,"y":0.3,"width":0.1,"height":0.05}'}
						bind:value={form.location_json}
						class="w-full text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none font-mono"
					/>
				</div>
				<div>
					<label class="block text-xs text-gray-500 mb-1" for="ef-patterns">{$i18n.t('Match title patterns (one per line, regex)')}</label>
					<textarea
						id="ef-patterns"
						bind:value={form.match_patterns_raw}
						rows="2"
						placeholder="e.g. MT-\\d+\nwire size mismatch"
						class="w-full text-xs rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1.5 outline-none font-mono"
					/>
				</div>
				<div class="flex justify-end gap-2 pt-2">
					<button class="px-3 py-1.5 text-sm rounded-xl border border-gray-200 dark:border-gray-800" on:click={() => (show = false)} disabled={saving}>
						{$i18n.t('Cancel')}
					</button>
					<button class="px-3 py-1.5 text-sm font-medium bg-black text-white dark:bg-white dark:text-black rounded-xl disabled:opacity-50" on:click={save} disabled={saving}>
						{saving ? $i18n.t('Saving...') : $i18n.t('Save')}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
