<script lang="ts">
	export let severity: string = 'info';

	const classes: Record<string, string> = {
		critical: 'bg-red-500/20 text-red-700 dark:text-red-200',
		major: 'bg-orange-500/20 text-orange-700 dark:text-orange-200',
		minor: 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-200',
		info: 'bg-blue-500/20 text-blue-700 dark:text-blue-200'
	};
</script>

<span
	class="text-xs font-medium {classes[severity] ?? classes['info']} px-1.5 py-0.5 rounded-md uppercase"
>
	{severity}
</span>
