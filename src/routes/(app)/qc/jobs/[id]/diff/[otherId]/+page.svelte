<script lang="ts">
	import { page } from '$app/stores';
	import RevisionDiffLayout from '$lib/components/qc/review/RevisionDiffLayout.svelte';

	$: prevJobId = $page.params.id;
	$: newJobId = $page.params.otherId;
</script>

{#key `${prevJobId}-${newJobId}`}
	<RevisionDiffLayout {prevJobId} {newJobId} />
{/key}
