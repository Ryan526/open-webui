<script lang="ts">
	import { page } from '$app/stores';
	import TemplateEditor from '$lib/components/qc/TemplateEditor.svelte';
</script>

<TemplateEditor templateId={$page.params.id} />
