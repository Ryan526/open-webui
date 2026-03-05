<script lang="ts">
	import { page } from '$app/stores';
	import ReviewLayout from '$lib/components/qc/review/ReviewLayout.svelte';
</script>

<ReviewLayout jobId={$page.params.id} />
