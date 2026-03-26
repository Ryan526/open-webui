<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { getQCPageImageFileUrl } from '$lib/apis/qc';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let documents: any[];
	export let jobId: string;
	export let selectedDocIndex: number;
	export let selectedPage: number;
	export let showAnnotated: boolean;
	export let findings: any[] = [];
	export let annotationMode: boolean = false;
	export let highlightedFindingId: string | null = null;
	export let annotationOpacity: number = 1;

	// Severity color map
	const SEVERITY_COLORS: Record<string, { fill: string; stroke: string }> = {
		critical: { fill: 'rgba(239,68,68,0.15)', stroke: 'rgb(239,68,68)' },
		major: { fill: 'rgba(249,115,22,0.15)', stroke: 'rgb(249,115,22)' },
		minor: { fill: 'rgba(234,179,8,0.15)', stroke: 'rgb(234,179,8)' },
		info: { fill: 'rgba(59,130,246,0.15)', stroke: 'rgb(59,130,246)' }
	};

	$: doc = documents[selectedDocIndex] || null;
	$: pageCount = doc?.page_count || 0;
	$: pageImages = doc?.meta?.page_images || {};

	$: {
		const ps = String(selectedPage);
		const fileId = pageImages[ps] || null;
		imageUrl = fileId ? getQCPageImageFileUrl(fileId) : null;
	}

	// Findings with location data for the current page
	$: locatedFindings = findings.filter((f) => f.location);

	let imageUrl: string | null = null;

	let zoom = 1;
	let containerEl: HTMLDivElement;
	let svgEl: SVGSVGElement;

	// Drawing state
	let drawing = false;
	let drawStart: { x: number; y: number } | null = null;
	let drawCurrent: { x: number; y: number } | null = null;

	$: drawRect = drawStart && drawCurrent
		? {
				x: Math.min(drawStart.x, drawCurrent.x),
				y: Math.min(drawStart.y, drawCurrent.y),
				width: Math.abs(drawCurrent.x - drawStart.x),
				height: Math.abs(drawCurrent.y - drawStart.y)
			}
		: null;

	const handleZoomIn = () => {
		zoom = Math.min(3, zoom + 0.25);
	};

	const handleZoomOut = () => {
		zoom = Math.max(0.25, zoom - 0.25);
	};

	const handleZoomReset = () => {
		zoom = 1;
	};

	const getNormalizedPos = (e: MouseEvent) => {
		const rect = svgEl.getBoundingClientRect();
		return {
			x: Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width)),
			y: Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height))
		};
	};

	const handleSvgMouseDown = (e: MouseEvent) => {
		if (!annotationMode) return;
		e.preventDefault();
		drawing = true;
		drawStart = getNormalizedPos(e);
		drawCurrent = drawStart;
	};

	const handleSvgMouseMove = (e: MouseEvent) => {
		if (!drawing) return;
		drawCurrent = getNormalizedPos(e);
	};

	const handleSvgMouseUp = (e: MouseEvent) => {
		if (!drawing || !drawRect) {
			drawing = false;
			return;
		}
		drawing = false;
		// Discard if too small
		if (drawRect.width < 0.005 || drawRect.height < 0.005) {
			drawStart = null;
			drawCurrent = null;
			return;
		}
		dispatch('annotationComplete', {
			location: { x: drawRect.x, y: drawRect.y, width: drawRect.width, height: drawRect.height }
		});
		drawStart = null;
		drawCurrent = null;
	};

	/** Get location rects for a finding — handles single dict or list of dicts */
	const getLocationRects = (
		location: any
	): Array<{ x: number; y: number; width: number; height: number }> => {
		if (Array.isArray(location)) return location;
		if (location && typeof location === 'object' && 'x' in location) return [location];
		return [];
	};

	const getColors = (severity: string) =>
		SEVERITY_COLORS[severity] || SEVERITY_COLORS.info;
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
			<button
				class="px-2 py-1 text-xs rounded-lg transition {showAnnotated
					? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
					: 'hover:bg-gray-100 dark:hover:bg-gray-800'}"
				on:click={() => (showAnnotated = !showAnnotated)}
				title={showAnnotated ? $i18n.t('Hide annotations') : $i18n.t('Show annotations')}
			>
				{showAnnotated ? $i18n.t('Annotated') : $i18n.t('Clean')}
			</button>

			{#if showAnnotated}
				<input
					type="range"
					min="0.05"
					max="1"
					step="0.05"
					bind:value={annotationOpacity}
					class="w-16 h-1 rounded-lg appearance-none cursor-pointer accent-blue-500"
					title={$i18n.t('Annotation opacity') + ': ' + Math.round(annotationOpacity * 100) + '%'}
				/>
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
				<div
					class="relative inline-block"
					style="transform: scale({zoom}); transform-origin: top center;"
				>
					<img
						src={imageUrl}
						alt="Page {selectedPage}"
						class="shadow-lg rounded block"
						draggable="false"
					/>
					<!-- SVG finding overlay -->
					<svg
						bind:this={svgEl}
						viewBox="0 0 1 1"
						preserveAspectRatio="none"
						class="absolute top-0 left-0 w-full h-full"
						style="pointer-events: {annotationMode ? 'all' : 'none'}; cursor: {annotationMode ? 'crosshair' : 'default'};"
						on:mousedown={handleSvgMouseDown}
						on:mousemove={handleSvgMouseMove}
						on:mouseup={handleSvgMouseUp}
						on:mouseleave={() => { if (drawing) { drawing = false; drawStart = null; drawCurrent = null; } }}
					>
						<!-- Finding overlays (controlled by toggle + opacity slider) -->
					{#if showAnnotated}
						<g opacity={annotationOpacity}>
							{#each locatedFindings as f, i}
								{@const colors = getColors(f.severity)}
								{#each getLocationRects(f.location) as loc}
									<rect
										x={loc.x}
										y={loc.y}
										width={loc.width}
										height={loc.height}
										fill={f.id === highlightedFindingId ? colors.stroke.replace('rgb', 'rgba').replace(')', ',0.3)') : colors.fill}
										stroke={colors.stroke}
										stroke-width={0.002}
										class="finding-rect"
										style="pointer-events: all; cursor: pointer;"
										on:mouseenter={() => dispatch('findingHover', f.id)}
										on:mouseleave={() => dispatch('findingHover', null)}
										on:click|stopPropagation={() => dispatch('findingClick', { findingId: f.id })}
									/>
								{/each}
								<!-- Number badge at first rect -->
								{@const firstLoc = getLocationRects(f.location)[0]}
								{#if firstLoc}
									{@const badgeR = 0.012}
									<circle
										cx={firstLoc.x + badgeR}
										cy={firstLoc.y + badgeR}
										r={badgeR}
										fill={colors.stroke}
										style="pointer-events: all; cursor: pointer;"
										on:click|stopPropagation={() => dispatch('findingClick', { findingId: f.id })}
									/>
									<text
										x={firstLoc.x + badgeR}
										y={firstLoc.y + badgeR}
										text-anchor="middle"
										dominant-baseline="central"
										fill="white"
										font-size={badgeR * 1.2}
										font-weight="bold"
										style="pointer-events: none;"
									>
										{f.finding_number || i + 1}
									</text>
								{/if}
							{/each}
						</g>
					{/if}

						<!-- Drawing preview -->
						{#if drawing && drawRect}
							<rect
								x={drawRect.x}
								y={drawRect.y}
								width={drawRect.width}
								height={drawRect.height}
								fill="rgba(59,130,246,0.1)"
								stroke="rgb(59,130,246)"
								stroke-width={0.002}
								stroke-dasharray="0.006 0.004"
							/>
						{/if}
					</svg>
				</div>
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
