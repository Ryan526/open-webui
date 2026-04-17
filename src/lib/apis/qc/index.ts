import { WEBUI_API_BASE_URL } from '$lib/constants';

const extractError = (err: unknown): string => {
	if (typeof err === 'string') return err;
	if (err && typeof err === 'object') {
		const anyErr = err as { detail?: unknown; message?: unknown };
		if (typeof anyErr.detail === 'string') return anyErr.detail;
		if (typeof anyErr.message === 'string') return anyErr.message;
	}
	return 'Request failed';
};

// =====================
// Templates
// =====================

export const getQCTemplates = async (token: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/templates`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const getQCSystemPrompts = async (token: string, categories?: object[]) => {
	let error = null;
	const params = new URLSearchParams();
	if (categories && categories.length > 0) {
		params.append('categories', JSON.stringify(categories));
	}
	const qs = params.toString();
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/system-prompts${qs ? '?' + qs : ''}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const getQCTemplateById = async (token: string, id: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/templates/${id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const createQCTemplate = async (
	token: string,
	data: {
		name: string;
		description?: string;
		system_prompt?: string;
		model_id?: string;
		meta?: object;
		access_grants?: object[];
	}
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/templates`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const updateQCTemplate = async (
	token: string,
	id: string,
	data: {
		name: string;
		description?: string;
		system_prompt?: string;
		model_id?: string;
		meta?: object;
		access_grants?: object[];
	},
	options?: { change_source?: string; change_summary?: string }
) => {
	let error = null;
	const params = new URLSearchParams();
	if (options?.change_source) params.append('change_source', options.change_source);
	if (options?.change_summary) params.append('change_summary', options.change_summary);
	const qs = params.toString();
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/templates/${id}${qs ? '?' + qs : ''}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify(data)
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const deleteQCTemplate = async (token: string, id: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/templates/${id}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const aiAssistChecklist = async (
	token: string,
	data: {
		knowledge_base_ids: string[];
		model_id?: string;
		existing_checklist?: object[];
	}
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/templates/ai-assist-checklist`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const cloneQCTemplate = async (token: string, id: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/templates/${id}/clone`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

// =====================
// Jobs
// =====================

export const getQCJobs = async (token: string, status?: string) => {
	let error = null;
	const params = new URLSearchParams();
	if (status) params.append('status', status);

	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs?${params.toString()}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const getQCJobById = async (token: string, id: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const createQCJob = async (
	token: string,
	data: {
		name: string;
		template_id?: string;
		template_version_id?: string;
		model_id?: string;
		system_prompt?: string;
		project_id?: string;
		previous_job_id?: string;
		revision_label?: string;
		meta?: object;
		access_grants?: object[];
	}
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const updateQCJob = async (
	token: string,
	id: string,
	data: {
		name: string;
		template_id?: string;
		model_id?: string;
		system_prompt?: string;
		meta?: object;
		access_grants?: object[];
	}
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${id}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const deleteQCJob = async (token: string, id: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${id}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const runQCJob = async (token: string, id: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${id}/run`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const exportQCJob = async (token: string, id: string, format: string = 'json') => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${id}/export?format=${format}`, {
		method: 'GET',
		headers: {
			Accept: format === 'csv' ? 'text/csv' : 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			if (format === 'csv') {
				return res.blob();
			}
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const selfImproveQCTemplate = async (token: string, jobId: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/self-improve`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

// =====================
// Documents
// =====================

export const getQCJobDocuments = async (token: string, jobId: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/documents`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const addQCJobDocument = async (
	token: string,
	jobId: string,
	file: File,
	documentType: string = 'subject'
) => {
	let error = null;
	const formData = new FormData();
	formData.append('file', file);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/documents/add?document_type=${documentType}`,
		{
			method: 'POST',
			headers: {
				authorization: `Bearer ${token}`
			},
			body: formData
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const removeQCJobDocument = async (token: string, jobId: string, docId: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/documents/${docId}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const getQCPageImageUrl = (
	token: string,
	jobId: string,
	docId: string,
	page: number,
	annotated: boolean = false
) => {
	// Uses the QC page image endpoint which serves the image directly
	return `${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/documents/${docId}/pages/${page}/image?annotated=${annotated}`;
};

export const getQCPageImageFileUrl = (fileId: string) => {
	// Uses the standard files API to serve image content (auth via cookie)
	return `${WEBUI_API_BASE_URL}/files/${fileId}/content`;
};

// =====================
// Findings
// =====================

export const getQCFindings = async (
	token: string,
	jobId: string,
	filters?: {
		page_number?: number;
		severity?: string;
		status?: string;
		document_id?: string;
	}
) => {
	let error = null;
	const params = new URLSearchParams();
	if (filters?.page_number !== undefined) params.append('page_number', filters.page_number.toString());
	if (filters?.severity) params.append('severity', filters.severity);
	if (filters?.status) params.append('status', filters.status);
	if (filters?.document_id) params.append('document_id', filters.document_id);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/findings?${params.toString()}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const createQCFinding = async (
	token: string,
	jobId: string,
	data: {
		document_id?: string;
		source?: string;
		page_number?: number;
		checklist_item_id?: string;
		severity?: string;
		title: string;
		description?: string;
		location?: object;
		meta?: object;
	}
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/findings`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const updateQCFinding = async (
	token: string,
	jobId: string,
	findingId: string,
	data: {
		severity?: string;
		status?: string;
		title?: string;
		description?: string;
		location?: object;
		meta?: object;
	}
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/findings/${findingId}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const deleteQCFinding = async (token: string, jobId: string, findingId: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/findings/${findingId}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

// =====================
// Comments
// =====================

export const getQCComments = async (token: string, jobId: string, findingId: string) => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/findings/${findingId}/comments`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const createQCComment = async (
	token: string,
	jobId: string,
	findingId: string,
	content: string
) => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/findings/${findingId}/comments`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ content })
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const deleteQCComment = async (
	token: string,
	jobId: string,
	findingId: string,
	commentId: string
) => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/findings/${findingId}/comments/${commentId}`,
		{
			method: 'DELETE',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

// =====================
// Template Versions
// =====================

export const getQCTemplateVersions = async (token: string, templateId: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/templates/${templateId}/versions`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const getQCTemplateVersion = async (
	token: string,
	templateId: string,
	versionNumber: number
) => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/templates/${templateId}/versions/${versionNumber}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const restoreQCTemplateVersion = async (
	token: string,
	templateId: string,
	versionNumber: number
) => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/templates/${templateId}/versions/${versionNumber}/restore`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const diffQCTemplateVersions = async (
	token: string,
	templateId: string,
	a: number,
	b: number
) => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/templates/${templateId}/versions/diff?a=${a}&b=${b}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

// =====================
// Projects (revision grouping)
// =====================

export const getQCProjects = async (token: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/projects`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const createQCProject = async (
	token: string,
	data: { name: string; description?: string; meta?: object }
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/projects`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const getQCProjectById = async (token: string, id: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/projects/${id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const updateQCProject = async (
	token: string,
	id: string,
	data: { name: string; description?: string; meta?: object }
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/projects/${id}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const deleteQCProject = async (token: string, id: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/projects/${id}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

// =====================
// Revisions / Diff
// =====================

export const createQCJobRevision = async (
	token: string,
	jobId: string,
	data: { revision_label?: string; name?: string } = {}
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/create-revision`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const getQCJobDiff = async (
	token: string,
	prevJobId: string,
	newJobId: string
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${prevJobId}/diff/${newJobId}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const applyQCJobDiff = async (
	token: string,
	prevJobId: string,
	newJobId: string,
	data: { create_resolved_ghosts?: boolean } = {}
) => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/jobs/${prevJobId}/diff/${newJobId}/apply`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify(data)
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

// =====================
// Reports (branded / redlined PDF)
// =====================

export const createQCReport = async (
	token: string,
	jobId: string,
	data: {
		report_type: 'branded_pdf' | 'redlined_pdf' | 'json' | 'csv';
		options?: Record<string, unknown>;
	}
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/reports`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const getQCReports = async (token: string, jobId: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/reports`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const getQCReport = async (token: string, jobId: string, reportId: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/reports/${reportId}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const getQCReportDownloadUrl = (jobId: string, reportId: string) => {
	return `${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/reports/${reportId}/download`;
};

export const downloadQCReport = async (
	token: string,
	jobId: string,
	reportId: string,
	filename: string
) => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/reports/${reportId}/download`,
		{
			method: 'GET',
			headers: { authorization: `Bearer ${token}` }
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.blob();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	if (res instanceof Blob) {
		const url = URL.createObjectURL(res);
		const a = document.createElement('a');
		a.href = url;
		a.download = filename;
		a.click();
		URL.revokeObjectURL(url);
	}
	return true;
};

export const deleteQCReport = async (token: string, jobId: string, reportId: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/reports/${reportId}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

// =====================
// Finding Intelligence (bulk, location, duplicates, suppression)
// =====================

export const bulkUpdateFindings = async (
	token: string,
	jobId: string,
	data: {
		finding_ids: string[];
		action:
			| 'confirm'
			| 'dismiss'
			| 'delete'
			| 'severity'
			| 'merge_duplicate'
			| 'unlink_duplicate';
		severity?: string;
		dismissal_reason?: string;
		canonical_finding_id?: string;
	}
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/findings/bulk`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const updateFindingLocation = async (
	token: string,
	jobId: string,
	findingId: string,
	data: { location?: object; reference_text?: string }
) => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/findings/${findingId}/location`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify(data)
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const getJobDuplicates = async (token: string, jobId: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/duplicates`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const recomputeDuplicates = async (token: string, jobId: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/duplicates/recompute`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export type QCSuppressionRule = {
	id: string;
	user_id: string;
	scope: 'template' | 'project' | 'global';
	template_id?: string | null;
	project_id?: string | null;
	name: string;
	enabled: number;
	match_type: 'title_exact' | 'title_regex' | 'title_contains' | 'checklist_item';
	match_value: string;
	severity_filter?: string | null;
	page_tag_filter?: string | null;
	reason?: string | null;
	hit_count: number;
	last_hit_at?: number | null;
	meta?: Record<string, unknown> | null;
	created_at: number;
	updated_at: number;
};

export const getQCSuppressionRules = async (
	token: string,
	filters?: { scope?: string; template_id?: string; project_id?: string }
) => {
	let error = null;
	const params = new URLSearchParams();
	if (filters?.scope) params.append('scope', filters.scope);
	if (filters?.template_id) params.append('template_id', filters.template_id);
	if (filters?.project_id) params.append('project_id', filters.project_id);
	const qs = params.toString();
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/suppression-rules${qs ? '?' + qs : ''}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const createQCSuppressionRule = async (
	token: string,
	data: Omit<QCSuppressionRule, 'id' | 'user_id' | 'hit_count' | 'last_hit_at' | 'created_at' | 'updated_at'>
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/suppression-rules`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const updateQCSuppressionRule = async (
	token: string,
	ruleId: string,
	data: Omit<QCSuppressionRule, 'id' | 'user_id' | 'hit_count' | 'last_hit_at' | 'created_at' | 'updated_at'>
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/suppression-rules/${ruleId}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const deleteQCSuppressionRule = async (token: string, ruleId: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/suppression-rules/${ruleId}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const getJobSuppressionEvents = async (token: string, jobId: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/suppression-events`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const createSuppressionRuleFromFinding = async (
	token: string,
	jobId: string,
	findingId: string,
	data: {
		scope?: 'template' | 'project' | 'global';
		match_type?: 'title_exact' | 'title_regex' | 'title_contains' | 'checklist_item';
		match_value?: string;
		name?: string;
		reason?: string;
	} = {}
) => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/findings/${findingId}/create-suppression-rule`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify(data)
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

// =====================
// Test Harness (Test Sets + Test Runs)
// =====================

export const getQCTestSets = async (token: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/test-sets`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const createQCTestSet = async (
	token: string,
	data: { name: string; description?: string; meta?: object }
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/test-sets`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const getQCTestSet = async (token: string, id: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/test-sets/${id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const updateQCTestSet = async (
	token: string,
	id: string,
	data: { name: string; description?: string; meta?: object }
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/test-sets/${id}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const deleteQCTestSet = async (token: string, id: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/test-sets/${id}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const addQCTestSetDocument = async (
	token: string,
	id: string,
	file: File
) => {
	let error = null;
	const formData = new FormData();
	formData.append('file', file);
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/test-sets/${id}/documents/add`, {
		method: 'POST',
		headers: { authorization: `Bearer ${token}` },
		body: formData
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const removeQCTestSetDocument = async (
	token: string,
	id: string,
	docId: string
) => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/test-sets/${id}/documents/${docId}`,
		{
			method: 'DELETE',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const getQCTestSetExpectedFindings = async (token: string, id: string) => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/test-sets/${id}/expected-findings`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const createQCTestSetExpectedFinding = async (
	token: string,
	id: string,
	data: {
		document_id: string;
		page_number?: number;
		checklist_item_id?: string;
		severity?: string;
		title: string;
		description?: string;
		location?: object;
		match_title_patterns?: string[];
		seeded_from_finding_id?: string;
	}
) => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/test-sets/${id}/expected-findings`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify(data)
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const updateQCTestSetExpectedFinding = async (
	token: string,
	id: string,
	efId: string,
	data: {
		document_id: string;
		page_number?: number;
		checklist_item_id?: string;
		severity?: string;
		title: string;
		description?: string;
		location?: object;
		match_title_patterns?: string[];
	}
) => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/test-sets/${id}/expected-findings/${efId}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify(data)
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const deleteQCTestSetExpectedFinding = async (
	token: string,
	id: string,
	efId: string
) => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/test-sets/${id}/expected-findings/${efId}`,
		{
			method: 'DELETE',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const seedTestSetFromJob = async (
	token: string,
	testSetId: string,
	jobId: string
) => {
	let error = null;
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/qc/test-sets/${testSetId}/seed-from-job/${jobId}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const runQCTestSet = async (
	token: string,
	testSetId: string,
	data: { template_id: string; template_version_id?: string; model_id_override?: string }
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/test-sets/${testSetId}/run`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const getQCTestRuns = async (token: string, testSetId?: string) => {
	let error = null;
	const params = new URLSearchParams();
	if (testSetId) params.append('test_set_id', testSetId);
	const qs = params.toString();
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/test-runs${qs ? '?' + qs : ''}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

export const getQCTestRunById = async (token: string, id: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/test-runs/${id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};

// =====================
// Checklist
// =====================

export const getQCChecklist = async (token: string, jobId: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/jobs/${jobId}/checklist`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = extractError(err);
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};
