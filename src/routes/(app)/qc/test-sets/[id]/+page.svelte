<script lang="ts">
	import { page } from '$app/stores';
	import TestSetEditor from '$lib/components/qc/test-sets/TestSetEditor.svelte';

	$: testSetId = $page.params.id;
</script>

{#key testSetId}
	<TestSetEditor {testSetId} />
{/key}
