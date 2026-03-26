import { WEBUI_API_BASE_URL } from '$lib/constants';

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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
	}
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/qc/templates/${id}`, {
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
		model_id?: string;
		system_prompt?: string;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
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
			error = err.detail;
			console.error(err);
			return null;
		});
	if (error) throw error;
	return res;
};
