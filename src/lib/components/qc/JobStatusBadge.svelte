<script lang="ts">
	export let status: string = 'pending';
	export let result: string | null = null;

	const statusClasses: Record<string, string> = {
		pending: 'bg-gray-500/20 text-gray-700 dark:text-gray-200',
		running: 'bg-blue-500/20 text-blue-700 dark:text-blue-200',
		completed: 'bg-green-500/20 text-green-700 dark:text-green-200',
		failed: 'bg-red-500/20 text-red-700 dark:text-red-200'
	};

	const resultClasses: Record<string, string> = {
		pass: 'bg-green-500/20 text-green-700 dark:text-green-200',
		fail: 'bg-red-500/20 text-red-700 dark:text-red-200',
		flagged: 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-200'
	};

	$: displayClass =
		status === 'completed' && result
			? resultClasses[result] ?? statusClasses[status]
			: statusClasses[status] ?? statusClasses['pending'];

	$: displayText = status === 'completed' && result ? result : status;
</script>

<span class="text-xs font-medium {displayClass} px-1.5 py-0.5 rounded-md uppercase">
	{displayText}
</span>
