<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, createEventDispatcher } from 'svelte';

	import { updateFindingLocation } from '$lib/apis/qc';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let jobId: string;
	export let finding: any;
	export let show: boolean;
	export let pendingAnnotation: { location: { x: number; y: number; width: number; height: number } } | null = null;

	let refText = '';
	let busy = false;

	$: if (show && finding) {
		refText = finding.meta?.reference_text || '';
	}

	const snapByText = async () => {
		if (!refText.trim()) {
			toast.error($i18n.t('Reference text is required'));
			return;
		}
		busy = true;
		try {
			const updated = await updateFindingLocation(localStorage.token, jobId, finding.id, {
				reference_text: refText.trim()
			});
			if (updated?.meta?.location_source === 'text_search') {
				toast.success($i18n.t('Snapped to text position'));
				dispatch('updated');
				show = false;
			} else {
				toast.error($i18n.t('No matching text on this page'));
			}
		} catch (e) {
			toast.error(`${e}`);
		}
		busy = false;
	};

	const applyDrawn = async () => {
		if (!pendingAnnotation?.location) {
			toast.error($i18n.t('Draw a rectangle on the page first'));
			return;
		}
		busy = true;
		try {
			await updateFindingLocation(localStorage.token, jobId, finding.id, {
				location: pendingAnnotation.location
			});
			toast.success($i18n.t('Location updated'));
			dispatch('annotationClear');
			dispatch('updated');
			show = false;
		} catch (e) {
			toast.error(`${e}`);
		}
		busy = false;
	};
</script>

{#if show && finding}
	<div class="fixed bottom-4 right-4 z-30 w-[min(360px,calc(100vw-2rem))] bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-xl">
		<div class="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-800">
			<h4 class="text-xs font-medium truncate">
				{$i18n.t('Edit location')} — #{finding.finding_number} {finding.title}
			</h4>
			<button
				class="text-xs text-gray-500 hover:text-gray-800"
				on:click={() => (show = false)}
			>
				✕
			</button>
		</div>
		<div class="p-3 space-y-3">
			<div>
				<label class="block text-xs text-gray-500 mb-1" for="location-ref-text">{$i18n.t('Snap by reference text')}</label>
				<div class="flex gap-2">
					<input
						id="location-ref-text"
						type="text"
						bind:value={refText}
						placeholder={$i18n.t('E.g. MT-415AB')}
						class="flex-1 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1 outline-none"
					/>
					<button
						class="px-2 py-1 text-xs rounded-lg bg-black text-white dark:bg-white dark:text-black disabled:opacity-50"
						disabled={busy}
						on:click={snapByText}
					>
						{$i18n.t('Snap')}
					</button>
				</div>
			</div>
			<div class="border-t border-gray-200 dark:border-gray-800 pt-2 space-y-1.5">
				<p class="text-xs text-gray-500">
					{$i18n.t('Or turn on Annotate mode above and drag a new rectangle, then apply:')}
				</p>
				{#if pendingAnnotation?.location}
					<div class="text-[10px] text-blue-500">
						{$i18n.t('Annotation ready')}: x={pendingAnnotation.location.x.toFixed(2)}, y={pendingAnnotation.location.y.toFixed(2)}
					</div>
				{:else}
					<div class="text-[10px] text-gray-400 italic">{$i18n.t('No annotation drawn yet')}</div>
				{/if}
				<button
					class="w-full px-2 py-1 text-xs rounded-lg border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50"
					disabled={busy || !pendingAnnotation?.location}
					on:click={applyDrawn}
				>
					{$i18n.t('Apply drawn rectangle')}
				</button>
			</div>
		</div>
	</div>
{/if}
