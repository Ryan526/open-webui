<script lang="ts">
	import { page } from '$app/stores';
	import ProjectDetail from '$lib/components/qc/ProjectDetail.svelte';

	$: projectId = $page.params.id;
</script>

{#key projectId}
	<ProjectDetail {projectId} />
{/key}
