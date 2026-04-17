<script lang="ts">
	import { page } from '$app/stores';
	import TestRunSummary from '$lib/components/qc/test-sets/TestRunSummary.svelte';

	$: runId = $page.params.id;
</script>

{#key runId}
	<TestRunSummary {runId} />
{/key}
