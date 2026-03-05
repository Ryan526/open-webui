<script lang="ts">
	import { getContext } from 'svelte';
	import { getQCPageImageFileUrl } from '$lib/apis/qc';

	const i18n = getContext('i18n');

	export let documents: any[];
	export let jobId: string;
	export let selectedDocIndex: number;
	export let selectedPage: number;
	export let showAnnotated: boolean;

	$: doc = documents[selectedDocIndex] || null;
	$: pageCount = doc?.page_count || 0;
	$: pageImages = doc?.meta?.page_images || {};
	$: annotatedImages = doc?.meta?.annotated_images || {};
	$: hasAnnotated = Object.keys(annotatedImages).length > 0;

	$: {
		const ps = String(selectedPage);
		let fileId = null;
		if (showAnnotated && hasAnnotated && annotatedImages[ps]) {
			fileId = annotatedImages[ps];
		} else if (pageImages[ps]) {
			fileId = pageImages[ps];
		}
		imageUrl = fileId ? getQCPageImageFileUrl(fileId) : null;
	}

	let imageUrl: string | null = null;

	let zoom = 1;
	let containerEl: HTMLDivElement;

	const handleZoomIn = () => {
		zoom = Math.min(3, zoom + 0.25);
	};

	const handleZoomOut = () => {
		zoom = Math.max(0.25, zoom - 0.25);
	};

	const handleZoomReset = () => {
		zoom = 1;
	};
</script>

<div class="flex flex-col h-full">
	<!-- Top bar: document selector + page nav + controls -->
	<div
		class="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-800 gap-2"
	>
		<!-- Document selector -->
		{#if documents.length > 1}
			<select
				bind:value={selectedDocIndex}
				class="text-xs rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1 outline-none max-w-[200px]"
				on:change={() => (selectedPage = 1)}
			>
				{#each documents as doc, i}
					<option value={i}>Doc {i + 1}: {doc.document_type}</option>
				{/each}
			</select>
		{/if}

		<!-- Page navigation -->
		<div class="flex items-center gap-1">
			<button
				class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition disabled:opacity-30"
				disabled={selectedPage <= 1}
				on:click={() => (selectedPage = Math.max(1, selectedPage - 1))}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="2"
					stroke="currentColor"
					class="size-4"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
				</svg>
			</button>

			<span class="text-xs tabular-nums">
				{selectedPage} / {pageCount}
			</span>

			<button
				class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition disabled:opacity-30"
				disabled={selectedPage >= pageCount}
				on:click={() => (selectedPage = Math.min(pageCount, selectedPage + 1))}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="2"
					stroke="currentColor"
					class="size-4"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
				</svg>
			</button>
		</div>

		<!-- Controls -->
		<div class="flex items-center gap-1">
			{#if hasAnnotated}
				<button
					class="px-2 py-1 text-xs rounded-lg transition {showAnnotated
						? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
						: 'hover:bg-gray-100 dark:hover:bg-gray-800'}"
					on:click={() => (showAnnotated = !showAnnotated)}
				>
					{showAnnotated ? $i18n.t('Annotated') : $i18n.t('Clean')}
				</button>
			{/if}

			<button
				class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition"
				on:click={handleZoomOut}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="size-4"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14" />
				</svg>
			</button>
			<button
				class="text-xs tabular-nums px-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition"
				on:click={handleZoomReset}
			>
				{Math.round(zoom * 100)}%
			</button>
			<button
				class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition"
				on:click={handleZoomIn}
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
			</button>
		</div>
	</div>

	<!-- Page thumbnails strip -->
	{#if pageCount > 1}
		<div
			class="flex gap-1 px-3 py-2 overflow-x-auto border-b border-gray-100 dark:border-gray-850 scrollbar-none"
		>
			{#each Array(pageCount) as _, i}
				<button
					class="shrink-0 w-10 h-12 rounded border-2 text-xs flex items-center justify-center transition {selectedPage ===
					i + 1
						? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700'
						: 'border-gray-200 dark:border-gray-700 hover:border-gray-400'}"
					on:click={() => (selectedPage = i + 1)}
				>
					{i + 1}
				</button>
			{/each}
		</div>
	{/if}

	<!-- Main page image -->
	<div class="flex-1 overflow-auto bg-gray-50 dark:bg-gray-950" bind:this={containerEl}>
		{#if imageUrl}
			<div class="flex justify-center p-4" style="min-height: 100%;">
				<img
					src={imageUrl}
					alt="Page {selectedPage}"
					class="shadow-lg rounded"
					style="transform: scale({zoom}); transform-origin: top center;"
					draggable="false"
				/>
			</div>
		{:else if pageCount === 0}
			<div class="flex items-center justify-center h-full text-gray-400">
				<p class="text-sm">{$i18n.t('No page images available for this document')}</p>
			</div>
		{:else}
			<div class="flex items-center justify-center h-full">
				<div class="text-center text-gray-400">
					<p class="text-sm">{$i18n.t('Loading page...')}</p>
				</div>
			</div>
		{/if}
	</div>
</div>
