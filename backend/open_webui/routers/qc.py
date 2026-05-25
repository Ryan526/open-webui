import json
import logging
import time
import uuid
from io import BytesIO
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    UploadFile,
    File,
    Query,
    status,
)
from fastapi.responses import StreamingResponse

from open_webui.models.qc import (
    QCTemplates,
    QCTemplateModel,
    QCTemplateForm,
    QCJobs,
    QCJobModel,
    QCJobForm,
    QCJobDocuments,
    QCJobDocumentModel,
    QCJobDocumentForm,
    QCFindings,
    QCFindingModel,
    QCFindingForm,
    QCFindingUpdateForm,
    QCComments,
    QCCommentModel,
    QCCommentForm,
    QCProjects,
    QCProjectModel,
    QCProjectForm,
    QCReports,
    QCReportModel,
    QCReportForm,
    QCSuppressionRules,
    QCSuppressionRuleModel,
    QCSuppressionRuleForm,
    QCSuppressionEvents,
    QCSuppressionEventModel,
    QCTemplateVersions,
    QCTemplateVersionModel,
    QCTestSets,
    QCTestSetModel,
    QCTestSetForm,
    QCTestSetDocuments,
    QCTestSetDocumentModel,
    QCTestSetExpectedFindings,
    QCTestSetExpectedFindingModel,
    QCTestSetExpectedFindingForm,
    QCTestRuns,
    QCTestRunModel,
)
from open_webui.models.files import Files, FileForm
from open_webui.models.knowledge import Knowledges
from open_webui.models.access_grants import AccessGrants
from open_webui.storage.provider import Storage

from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import has_permission
from open_webui.internal.db import get_async_db_context
from sqlalchemy import update as sa_update
from open_webui.models.qc import QCTemplate
from open_webui.constants import ERROR_MESSAGES
from open_webui.config import QC_MAX_UPLOAD_BYTES, QC_MAX_PDF_PAGES

ALLOWED_UPLOAD_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/msword",
}
ALLOWED_UPLOAD_EXTENSIONS = (
    ".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".xlsx", ".xls", ".docx", ".doc",
)

log = logging.getLogger(__name__)

router = APIRouter()


############################
# Helpers
############################


async def _check_qc_access(request, user):
    """Check if user has QC access permission."""
    if user.role != "admin" and not await has_permission(
        user.id,
        "features.qc",
        request.app.state.config.USER_PERMISSIONS,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


############################
# System Prompts (read-only)
############################


@router.get("/system-prompts")
async def get_system_prompts(
    request: Request,
    categories: Optional[str] = Query(None),
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    from open_webui.utils.qc_analysis import (
        QC_SYSTEM_PROMPT,
        EXTRACTION_SYSTEM_PROMPT,
        CROSS_REFERENCE_SYSTEM_PROMPT,
        SELF_IMPROVE_SYSTEM_PROMPT,
        CHECKLIST_ASSIST_SYSTEM_PROMPT,
        build_extraction_prompt,
        build_correlation_prompt,
        _migrate_legacy_categories,
    )

    if categories:
        try:
            parsed = json.loads(categories)
            migrated = _migrate_legacy_categories(parsed)
            extraction_prompt = build_extraction_prompt(migrated)
            correlation_prompt = build_correlation_prompt(migrated)
        except (json.JSONDecodeError, TypeError):
            extraction_prompt = EXTRACTION_SYSTEM_PROMPT
            correlation_prompt = CROSS_REFERENCE_SYSTEM_PROMPT
    else:
        extraction_prompt = EXTRACTION_SYSTEM_PROMPT
        correlation_prompt = CROSS_REFERENCE_SYSTEM_PROMPT

    return {
        "qc_system_prompt": QC_SYSTEM_PROMPT,
        "extraction_system_prompt": extraction_prompt,
        "cross_reference_system_prompt": correlation_prompt,
        "self_improve_system_prompt": SELF_IMPROVE_SYSTEM_PROMPT,
        "checklist_assist_system_prompt": CHECKLIST_ASSIST_SYSTEM_PROMPT,
    }


async def _check_job_access(job, user, write=False):
    """Check if user can access a job."""
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if user.role == "admin":
        return
    if job.user_id == user.id:
        return
    permission = "write" if write else "read"
    if await AccessGrants.has_access(
        user_id=user.id,
        resource_type="qc_job",
        resource_id=job.id,
        permission=permission,
    ):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
    )


async def _check_template_access(template, user, write=False):
    """Check if user can access a template."""
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if user.role == "admin":
        return
    if template.user_id == user.id:
        return
    permission = "write" if write else "read"
    if await AccessGrants.has_access(
        user_id=user.id,
        resource_type="qc_template",
        resource_id=template.id,
        permission=permission,
    ):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
    )


async def _check_project_access(project, user, write=False):
    """Check if user can access a project."""
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if user.role == "admin":
        return
    if project.user_id == user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
    )


############################
# Project Endpoints
############################


@router.get("/projects", response_model=list[QCProjectModel])
async def get_projects(
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    if user.role == "admin":
        return await QCProjects.get_projects()
    return await QCProjects.get_projects(user_id=user.id)


@router.post("/projects", response_model=Optional[QCProjectModel])
async def create_project(
    request: Request,
    form_data: QCProjectForm,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    project = await QCProjects.insert_new_project(user.id, form_data)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create project",
        )
    return project


@router.get("/projects/{id}")
async def get_project_by_id(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    project = await QCProjects.get_project_by_id(id)
    await _check_project_access(project, user)
    jobs = await QCProjects.get_jobs_by_project_id(id)
    return {**project.model_dump(), "jobs": [j.model_dump() for j in jobs]}


@router.post("/projects/{id}", response_model=Optional[QCProjectModel])
async def update_project(
    id: str,
    request: Request,
    form_data: QCProjectForm,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    project = await QCProjects.get_project_by_id(id)
    await _check_project_access(project, user, write=True)
    return await QCProjects.update_project_by_id(id, form_data)


@router.delete("/projects/{id}")
async def delete_project(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    project = await QCProjects.get_project_by_id(id)
    await _check_project_access(project, user, write=True)
    await QCProjects.delete_project_by_id(id)
    return {"status": True}


############################
# Template Endpoints
############################


@router.post("/templates/ai-assist-checklist")
async def ai_assist_checklist(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
):
    """Use AI to generate or suggest checklist items from knowledge base content."""
    await _check_qc_access(request, user)

    knowledge_base_ids = form_data.get("knowledge_base_ids", [])
    if not knowledge_base_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one knowledge base must be provided",
        )

    model_id = form_data.get("model_id")
    if not model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A model must be selected",
        )

    existing_checklist = form_data.get("existing_checklist")

    from open_webui.utils.qc_analysis import generate_checklist_suggestions

    suggestions = await generate_checklist_suggestions(
        request, knowledge_base_ids, model_id, existing_checklist, user
    )

    return suggestions


@router.get("/templates", response_model=list[QCTemplateModel])
async def get_templates(
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    templates = await QCTemplates.get_templates()
    if user.role == "admin":
        return templates
    # Filter to templates user owns or has access to
    return [
        t
        for t in templates
        if t.user_id == user.id
        or await AccessGrants.has_access(
            user_id=user.id,
            resource_type="qc_template",
            resource_id=t.id,
            permission="read",
        )
    ]


@router.get("/templates/{id}", response_model=Optional[QCTemplateModel])
async def get_template_by_id(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    template = await QCTemplates.get_template_by_id(id)
    await _check_template_access(template, user)
    return template


@router.post("/templates", response_model=Optional[QCTemplateModel])
async def create_template(
    request: Request,
    form_data: QCTemplateForm,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    template = await QCTemplates.insert_new_template(user.id, form_data)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create template",
        )
    return template


@router.post("/templates/{id}", response_model=Optional[QCTemplateModel])
async def update_template(
    id: str,
    request: Request,
    form_data: QCTemplateForm,
    change_source: Optional[str] = Query(None),
    change_summary: Optional[str] = Query(None),
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    template = await QCTemplates.get_template_by_id(id)
    await _check_template_access(template, user, write=True)
    source = change_source if change_source in ("manual", "self_improve", "restore") else "manual"
    updated = await QCTemplates.update_template_by_id(
        id,
        form_data,
        change_source=source,
        change_summary=change_summary,
        actor_user_id=user.id,
    )
    return updated


@router.delete("/templates/{id}")
async def delete_template(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    template = await QCTemplates.get_template_by_id(id)
    await _check_template_access(template, user, write=True)
    await QCTemplates.delete_template_by_id(id)
    return {"status": True}


@router.post("/templates/{id}/clone", response_model=Optional[QCTemplateModel])
async def clone_template(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    template = await QCTemplates.get_template_by_id(id)
    await _check_template_access(template, user)

    clone_form = QCTemplateForm(
        name=f"{template.name} (Copy)",
        description=template.description,
        system_prompt=template.system_prompt,
        model_id=template.model_id,
        meta=template.meta,
    )
    return await QCTemplates.insert_new_template(user.id, clone_form)


############################
# Job Endpoints
############################


@router.get("/jobs", response_model=list[QCJobModel])
async def get_jobs(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    if user.role == "admin":
        jobs = await QCJobs.get_jobs(status=status_filter)
    else:
        jobs = await QCJobs.get_jobs(user_id=user.id, status=status_filter)
    return jobs


@router.get("/jobs/{id}", response_model=Optional[QCJobModel])
async def get_job_by_id(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(id)
    await _check_job_access(job, user)
    return job


@router.post("/jobs", response_model=Optional[QCJobModel])
async def create_job(
    request: Request,
    form_data: QCJobForm,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)

    # If template_id provided, snapshot template settings (optionally from a pinned version)
    if form_data.template_id:
        template = await QCTemplates.get_template_by_id(form_data.template_id)
        if template:
            # Resolve version to use: explicit pin > template's current_version_id
            pinned_version = None
            pin_version_id = form_data.template_version_id or template.current_version_id
            if pin_version_id:
                pinned_version = await QCTemplateVersions.get_version_by_id(pin_version_id)
                if pinned_version and pinned_version.template_id != template.id:
                    pinned_version = None

            source_system_prompt = (
                pinned_version.system_prompt if pinned_version else template.system_prompt
            )
            source_model_id = (
                pinned_version.model_id if pinned_version else template.model_id
            )
            source_meta = (pinned_version.meta if pinned_version else template.meta) or {}

            if not form_data.model_id:
                form_data.model_id = source_model_id
            if not form_data.system_prompt:
                form_data.system_prompt = source_system_prompt

            # Always persist the pinned version id on the job (if any resolvable)
            if pinned_version and not form_data.template_version_id:
                form_data.template_version_id = pinned_version.id

            template_meta = source_meta
            job_meta = form_data.meta or {}
            job_meta["checklist_snapshot"] = template_meta.get("checklist", [])
            knowledge_base_ids = template_meta.get("knowledge_base_ids", [])
            job_meta["knowledge_base_ids"] = knowledge_base_ids
            # Snapshot cross-reference analysis config
            xref_config = template_meta.get("cross_reference_analysis")
            if xref_config:
                job_meta["cross_reference_analysis"] = xref_config

            # Fetch KB content for AI context
            if knowledge_base_ids:
                kb_parts = []
                for kb_id in knowledge_base_ids:
                    try:
                        kb_files = await Knowledges.get_files_by_id(kb_id)
                        for f in kb_files:
                            file_content = (f.data or {}).get("content", "")
                            if file_content:
                                file_name = (f.meta or {}).get(
                                    "name", f.filename
                                )
                                kb_parts.append(
                                    f"=== {file_name} ===\n{file_content}"
                                )
                    except Exception as e:
                        log.warning(
                            f"Failed to fetch KB {kb_id} content: {e}"
                        )
                kb_context = "\n\n".join(kb_parts)
                max_kb_chars = 500_000
                kb_original_chars = len(kb_context)
                if kb_original_chars > max_kb_chars:
                    log.warning(
                        f"KB context truncated from {kb_original_chars} to {max_kb_chars} chars"
                    )
                    kb_context = kb_context[:max_kb_chars]
                    job_meta["kb_truncated"] = True
                    job_meta["kb_original_chars"] = kb_original_chars
                    job_meta["kb_used_chars"] = max_kb_chars
                if kb_context:
                    job_meta["kb_context"] = kb_context

            form_data.meta = job_meta

    job = await QCJobs.insert_new_job(user.id, form_data)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create job",
        )
    return job


@router.post("/jobs/{id}", response_model=Optional[QCJobModel])
async def update_job(
    id: str,
    request: Request,
    form_data: QCJobForm,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(id)
    await _check_job_access(job, user, write=True)
    return await QCJobs.update_job_by_id(id, form_data)


@router.delete("/jobs/{id}")
async def delete_job(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(id)
    await _check_job_access(job, user, write=True)
    await QCJobs.delete_job_by_id(id)
    return {"status": True}


@router.post("/jobs/{id}/run")
async def run_job(
    id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user=Depends(get_verified_user),
):
    """Start QC analysis for a job. Runs in background."""
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(id)
    await _check_job_access(job, user, write=True)

    if job.status not in ("pending", "failed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is {job.status}; cannot start analysis. Create a new job to re-analyze.",
        )

    if not job.model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No model selected for this job",
        )

    # Check documents exist
    documents = await QCJobDocuments.get_documents_by_job_id(id)
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No documents uploaded for this job",
        )

    from open_webui.utils.qc_analysis import run_qc_job

    background_tasks.add_task(run_qc_job, request, id, user)
    await QCJobs.update_job_status(id, "running")

    return {"status": True, "message": "QC analysis started"}


@router.post("/jobs/{job_id}/self-improve")
async def self_improve_template(
    job_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    """Analyze reviewed findings and suggest improvements to the source template."""
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user)

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job must be completed before self-improvement",
        )

    if not job.template_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job has no associated template",
        )

    template = await QCTemplates.get_template_by_id(job.template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source template no longer exists",
        )

    await _check_template_access(template, user, write=True)

    findings = await QCFindings.get_findings_by_job_id(job_id)
    has_reviewed = any(f.status in ("confirmed", "dismissed") for f in findings)
    has_human = any(f.source == "human" for f in findings)
    if not has_reviewed and not has_human:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one finding must be confirmed, dismissed, or manually added",
        )

    from open_webui.utils.qc_analysis import generate_self_improve_suggestions

    suggestions = await generate_self_improve_suggestions(
        request, job, template, findings, user
    )

    suggestions["template_id"] = template.id
    suggestions["template_updated_at"] = template.updated_at
    suggestions["job_created_at"] = job.created_at

    return suggestions


@router.get("/jobs/{id}/export")
async def export_job(
    id: str,
    format: str = Query("json"),
    request: Request = None,
    user=Depends(get_verified_user),
):
    """Export job findings as JSON or CSV."""
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(id)
    await _check_job_access(job, user)

    findings = await QCFindings.get_findings_by_job_id(id)
    documents = await QCJobDocuments.get_documents_by_job_id(id)

    if format == "csv":
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Finding #",
            "Page",
            "Severity",
            "Status",
            "Title",
            "Description",
            "Source",
        ])
        for f in findings:
            writer.writerow([
                f.finding_number,
                f.page_number,
                f.severity,
                f.status,
                f.title,
                f.description or "",
                f.source,
            ])
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=qc_job_{id}.csv"
            },
        )

    # Default JSON export
    export_data = {
        "job": job.model_dump(),
        "documents": [d.model_dump() for d in documents],
        "findings": [f.model_dump() for f in findings],
    }
    return export_data


############################
# Document Endpoints
############################


@router.post("/jobs/{job_id}/documents/add")
async def add_document(
    job_id: str,
    request: Request,
    file: UploadFile = File(...),
    document_type: str = Query("subject"),
    user=Depends(get_verified_user),
):
    """Upload a document (PDF/image) to a job and convert to page images."""
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user, write=True)

    if job.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add documents while job is running",
        )

    filename = file.filename or "upload"
    content_type = file.content_type or ""
    lowered = filename.lower()

    # Content-type / extension allow-list
    ext_ok = any(lowered.endswith(ext) for ext in ALLOWED_UPLOAD_EXTENSIONS)
    type_ok = content_type in ALLOWED_UPLOAD_CONTENT_TYPES or content_type.startswith("image/")
    if not (ext_ok or type_ok):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported file type. Allowed: PDF, PNG, JPG, TIFF, XLSX, DOCX."
            ),
        )

    # Enforce max upload size while reading (avoid loading huge files into memory)
    file_bytes = bytearray()
    chunk_size = 1024 * 1024
    while True:
        chunk = file.file.read(chunk_size)
        if not chunk:
            break
        file_bytes.extend(chunk)
        if len(file_bytes) > QC_MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"File exceeds maximum upload size of "
                    f"{QC_MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
                ),
            )
    file_bytes = bytes(file_bytes)

    # Upload the original file
    file_id = str(uuid.uuid4())
    storage_filename = f"{file_id}_{filename}"

    contents, file_path = Storage.upload_file(
        BytesIO(file_bytes),
        storage_filename,
        {
            "OpenWebUI-User-Id": user.id,
            "OpenWebUI-File-Id": file_id,
        },
    )

    # Save file record
    await Files.insert_new_file(
        user.id,
        FileForm(
            id=file_id,
            filename=storage_filename,
            path=file_path,
            meta={
                "name": filename,
                "content_type": content_type,
                "size": len(contents),
                "qc_job_id": job_id,
            },
        ),
    )

    # Create QC document record
    doc_form = QCJobDocumentForm(file_id=file_id, document_type=document_type)
    doc = await QCJobDocuments.insert_document(job_id, doc_form)

    # Convert to page images
    page_images = {}

    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        from open_webui.utils.qc_document import convert_pdf_to_pages

        actual_file_path = Storage.get_file(file_path)
        pages = convert_pdf_to_pages(actual_file_path)

        if len(pages) > QC_MAX_PDF_PAGES:
            await QCJobDocuments.delete_document(doc.id)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"PDF has {len(pages)} pages; maximum is {QC_MAX_PDF_PAGES}."
                ),
            )

        for i, page_bytes in enumerate(pages):
            page_num = i + 1
            page_file_id = str(uuid.uuid4())
            page_filename = f"{page_file_id}_page_{page_num}.png"

            _, page_file_path = Storage.upload_file(
                BytesIO(page_bytes),
                page_filename,
                {
                    "OpenWebUI-User-Id": user.id,
                    "OpenWebUI-File-Id": page_file_id,
                },
            )

            await Files.insert_new_file(
                user.id,
                FileForm(
                    id=page_file_id,
                    filename=page_filename,
                    path=page_file_path,
                    meta={
                        "name": page_filename,
                        "content_type": "image/png",
                        "size": len(page_bytes),
                        "qc_job_id": job_id,
                        "qc_document_id": doc.id,
                        "page_number": page_num,
                    },
                ),
            )
            page_images[str(page_num)] = page_file_id

        await QCJobDocuments.update_document(
            doc.id,
            page_count=len(pages),
            status="pending",
            meta={"page_images": page_images},
        )
    elif content_type and content_type.startswith("image/"):
        # Single image - treat as page 1
        page_images["1"] = file_id
        await QCJobDocuments.update_document(
            doc.id,
            page_count=1,
            status="pending",
            meta={"page_images": page_images},
        )
    else:
        # Non-visual document (Excel, DOCX, etc.) - mark as pending for text analysis
        await QCJobDocuments.update_document(
            doc.id,
            page_count=0,
            status="pending",
            meta={"page_images": {}},
        )

    return await QCJobDocuments.get_document_by_id(doc.id)


@router.get("/jobs/{job_id}/documents", response_model=list[QCJobDocumentModel])
async def get_documents(
    job_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user)
    return await QCJobDocuments.get_documents_by_job_id(job_id)


@router.delete("/jobs/{job_id}/documents/{doc_id}")
async def remove_document(
    job_id: str,
    doc_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user, write=True)

    if job.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove documents while job is running",
        )

    await QCJobDocuments.delete_document(doc_id)
    return {"status": True}


@router.get("/jobs/{job_id}/documents/{doc_id}/pages/{page}/image")
async def get_page_image(
    job_id: str,
    doc_id: str,
    page: int,
    annotated: bool = Query(False),
    request: Request = None,
    user=Depends(get_verified_user),
):
    """Get a page image (clean or annotated)."""
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user)

    doc = await QCJobDocuments.get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    meta = doc.meta or {}
    page_str = str(page)

    if annotated:
        images = meta.get("annotated_images", {})
    else:
        images = meta.get("page_images", {})

    file_id = images.get(page_str)
    if not file_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page} image not found",
        )

    file_record = await Files.get_file_by_id(file_id)
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found",
        )

    file_path = Storage.get_file(file_record.path)
    with open(file_path, "rb") as f:
        image_bytes = f.read()

    return StreamingResponse(
        BytesIO(image_bytes),
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename=page_{page}.png"},
    )


############################
# Finding Endpoints
############################


@router.get("/jobs/{job_id}/findings", response_model=list[QCFindingModel])
async def get_findings(
    job_id: str,
    request: Request,
    page_number: Optional[int] = None,
    severity: Optional[str] = None,
    finding_status: Optional[str] = Query(None, alias="status"),
    document_id: Optional[str] = None,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user)

    return await QCFindings.get_findings_by_job_id(
        job_id,
        page_number=page_number,
        severity=severity,
        status=finding_status,
        document_id=document_id,
    )


@router.post("/jobs/{job_id}/findings", response_model=Optional[QCFindingModel])
async def create_finding(
    job_id: str,
    request: Request,
    form_data: QCFindingForm,
    user=Depends(get_verified_user),
):
    """Create a manual (human) finding."""
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user, write=True)

    finding = await QCFindings.insert_finding(user.id, job_id, form_data)
    return finding


@router.post(
    "/jobs/{job_id}/findings/{finding_id}",
    response_model=Optional[QCFindingModel],
)
async def update_finding(
    job_id: str,
    finding_id: str,
    request: Request,
    form_data: QCFindingUpdateForm,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user, write=True)

    finding = await QCFindings.get_finding_by_id(finding_id)
    if not finding or finding.job_id != job_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )

    return await QCFindings.update_finding(finding_id, form_data)


@router.delete("/jobs/{job_id}/findings/{finding_id}")
async def delete_finding(
    job_id: str,
    finding_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user, write=True)

    finding = await QCFindings.get_finding_by_id(finding_id)
    if not finding or finding.job_id != job_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )

    await QCFindings.delete_finding(finding_id)
    return {"status": True}


############################
# Comment Endpoints
############################


@router.get(
    "/jobs/{job_id}/findings/{finding_id}/comments",
    response_model=list[QCCommentModel],
)
async def get_comments(
    job_id: str,
    finding_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user)

    return await QCComments.get_comments_by_finding_id(finding_id)


@router.post(
    "/jobs/{job_id}/findings/{finding_id}/comments",
    response_model=Optional[QCCommentModel],
)
async def create_comment(
    job_id: str,
    finding_id: str,
    request: Request,
    form_data: QCCommentForm,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user, write=True)

    finding = await QCFindings.get_finding_by_id(finding_id)
    if not finding or finding.job_id != job_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )

    return await QCComments.insert_comment(user.id, finding_id, job_id, form_data)


@router.delete("/jobs/{job_id}/findings/{finding_id}/comments/{comment_id}")
async def delete_comment(
    job_id: str,
    finding_id: str,
    comment_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user, write=True)

    comment = await QCComments.get_comment_by_id(comment_id)
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    # Only comment author or admin can delete
    if comment.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    await QCComments.delete_comment(comment_id)
    return {"status": True}


############################
# Checklist Endpoints
############################


@router.get("/jobs/{job_id}/checklist")
async def get_checklist_status(
    job_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    """Get checklist items with their findings count/status."""
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user)

    meta = job.meta or {}
    checklist = meta.get("checklist_snapshot", [])
    findings = await QCFindings.get_findings_by_job_id(job_id)

    checklist_status = []
    for item in checklist:
        item_id = item.get("id")
        related_findings = [
            f for f in findings if f.checklist_item_id == item_id
        ]
        checklist_status.append(
            {
                **item,
                "findings_count": len(related_findings),
                "has_critical": any(
                    f.severity == "critical" for f in related_findings
                ),
                "has_major": any(
                    f.severity == "major" for f in related_findings
                ),
                "all_resolved": all(
                    f.status in ("dismissed", "resolved")
                    for f in related_findings
                )
                if related_findings
                else True,
            }
        )

    return checklist_status


############################
# Revision Endpoints
############################


@router.post("/jobs/{id}/create-revision", response_model=Optional[QCJobModel])
async def create_revision(
    id: str,
    request: Request,
    form_data: Optional[dict] = None,
    user=Depends(get_verified_user),
):
    """Create a shell follow-up job that references the given job as its previous revision.

    The new job inherits the template, model, system_prompt, and (transitively) the
    KB context of the source job. Documents are NOT copied — the client re-uploads
    through the standard documents/add endpoint.
    """
    await _check_qc_access(request, user)
    prev_job = await QCJobs.get_job_by_id(id)
    await _check_job_access(prev_job, user, write=True)

    body = form_data or {}
    revision_label = body.get("revision_label") or None
    name = body.get("name") or f"{prev_job.name} (Rev {(prev_job.revision_index or 0) + 1})"

    new_meta: dict = {}
    # Carry KB/checklist snapshots forward so analysis works without needing template re-resolve.
    prev_meta = prev_job.meta or {}
    for key in (
        "checklist_snapshot",
        "knowledge_base_ids",
        "cross_reference_analysis",
        "kb_context",
        "kb_truncated",
        "kb_original_chars",
        "kb_used_chars",
        "branding",
    ):
        if key in prev_meta:
            new_meta[key] = prev_meta[key]

    new_form = QCJobForm(
        name=name,
        template_id=prev_job.template_id,
        model_id=prev_job.model_id,
        system_prompt=prev_job.system_prompt,
        project_id=prev_job.project_id,
        previous_job_id=prev_job.id,
        revision_label=revision_label,
        meta=new_meta,
    )
    created = await QCJobs.insert_new_job(user.id, new_form)
    if not created:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create revision",
        )
    return created


@router.get("/jobs/{id}/diff/{other_id}")
async def get_job_diff(
    id: str,
    other_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    """Compute the revision diff between two jobs (id = previous, other_id = new)."""
    await _check_qc_access(request, user)
    prev = await QCJobs.get_job_by_id(id)
    await _check_job_access(prev, user)
    new = await QCJobs.get_job_by_id(other_id)
    await _check_job_access(new, user)

    from open_webui.utils.qc_revisions import compute_diff

    return await compute_diff(prev.id, new.id)


@router.post("/jobs/{id}/diff/{other_id}/apply")
async def apply_job_diff(
    id: str,
    other_id: str,
    request: Request,
    form_data: Optional[dict] = None,
    user=Depends(get_verified_user),
):
    """Persist revision_state / previous_finding_id on the new job's findings.

    Body (optional): {"create_resolved_ghosts": bool}
    """
    await _check_qc_access(request, user)
    prev = await QCJobs.get_job_by_id(id)
    await _check_job_access(prev, user)
    new = await QCJobs.get_job_by_id(other_id)
    await _check_job_access(new, user, write=True)

    body = form_data or {}
    ghosts = bool(body.get("create_resolved_ghosts", False))

    from open_webui.utils.qc_revisions import apply_diff_to_new_job

    return await apply_diff_to_new_job(prev.id, new.id, create_resolved_ghosts=ghosts)


############################
# Report Endpoints
############################


async def _generate_report_background(
    report_id: str,
    job_id: str,
    user_id: str,
    report_type: str,
    options: dict,
):
    """Background task: generate the report file and update status."""
    try:
        await QCReports.update_report(report_id, status="generating")

        job = await QCJobs.get_job_by_id(job_id)
        documents = await QCJobDocuments.get_documents_by_job_id(job_id)
        findings = await QCFindings.get_findings_by_job_id(job_id)

        from open_webui.utils.qc_report import (
            generate_branded_pdf,
            generate_redlined_pdf,
            persist_report_bytes,
            _resolve_branding,
        )

        if report_type == "branded_pdf":
            template_meta = None
            if job and job.template_id:
                tpl = await QCTemplates.get_template_by_id(job.template_id)
                template_meta = tpl.meta if tpl else None
            branding = _resolve_branding(job.meta if job else None, template_meta)

            include_severities = options.get("include_severities")
            include_dismissed = bool(options.get("include_dismissed", False))
            pdf_bytes, meta = generate_branded_pdf(
                job,
                documents,
                findings,
                branding=branding,
                include_severities=include_severities,
                include_dismissed=include_dismissed,
            )
            filename = f"qc_report_{job_id}.pdf"
            file_id = persist_report_bytes(user_id, job_id, filename, pdf_bytes, "application/pdf")
            await QCReports.update_report(
                report_id, status="ready", file_id=file_id, meta=meta
            )

        elif report_type == "redlined_pdf":
            doc_id = options.get("document_id")
            if not doc_id:
                raise RuntimeError("document_id required for redlined_pdf")
            target_doc = next((d for d in documents if d.id == doc_id), None)
            if target_doc is None:
                raise RuntimeError("document not found")
            doc_findings = [f for f in findings if f.document_id == doc_id]
            pdf_bytes, meta = generate_redlined_pdf(job, target_doc, doc_findings)
            doc_meta = target_doc.meta or {}
            base_name = (doc_meta.get("name") or f"document_{doc_id}").rsplit(".", 1)[0]
            filename = f"{base_name}_redlined.pdf"
            file_id = persist_report_bytes(user_id, job_id, filename, pdf_bytes, "application/pdf")
            await QCReports.update_report(
                report_id, status="ready", file_id=file_id, meta=meta
            )
        else:
            raise RuntimeError(f"Unsupported report_type: {report_type}")

    except Exception as e:
        log.exception(f"Report generation failed for report_id={report_id}")
        await QCReports.update_report(
            report_id,
            status="failed",
            meta={"error": str(e)},
        )


@router.post("/jobs/{id}/reports", response_model=Optional[QCReportModel])
async def create_report(
    id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    form_data: dict,
    user=Depends(get_verified_user),
):
    """Create a report generation task. Runs asynchronously; poll via GET reports/{id}."""
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(id)
    await _check_job_access(job, user)

    report_type = form_data.get("report_type")
    if report_type not in ("branded_pdf", "redlined_pdf", "json", "csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid report_type",
        )

    options = form_data.get("options") or {}

    report = await QCReports.insert_report(
        user.id,
        id,
        QCReportForm(report_type=report_type, meta={"options": options}),
    )
    if not report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create report",
        )

    if report_type in ("branded_pdf", "redlined_pdf"):
        background_tasks.add_task(
            _generate_report_background,
            report.id,
            id,
            user.id,
            report_type,
            options,
        )
    else:
        # json/csv can still be served by the existing /export endpoint; mark as ready
        # with no file_id — clients should prefer /export for those formats.
        await QCReports.update_report(
            report.id,
            status="ready",
            meta={"note": "use /jobs/{id}/export for json/csv formats"},
        )

    return await QCReports.get_report_by_id(report.id)


@router.get("/jobs/{id}/reports", response_model=list[QCReportModel])
async def list_reports(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(id)
    await _check_job_access(job, user)
    return await QCReports.get_reports_by_job_id(id)


@router.get("/jobs/{id}/reports/{report_id}", response_model=Optional[QCReportModel])
async def get_report(
    id: str,
    report_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(id)
    await _check_job_access(job, user)
    report = await QCReports.get_report_by_id(report_id)
    if not report or report.job_id != id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    return report


@router.get("/jobs/{id}/reports/{report_id}/download")
async def download_report(
    id: str,
    report_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(id)
    await _check_job_access(job, user)
    report = await QCReports.get_report_by_id(report_id)
    if not report or report.job_id != id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    if report.status != "ready" or not report.file_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Report is {report.status}; not ready for download",
        )
    file_record = await Files.get_file_by_id(report.file_id)
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file missing",
        )
    file_path = Storage.get_file(file_record.path)
    with open(file_path, "rb") as f:
        data = f.read()
    download_name = (file_record.meta or {}).get("name") or file_record.filename or "report.pdf"
    return StreamingResponse(
        BytesIO(data),
        media_type=(file_record.meta or {}).get("content_type", "application/pdf"),
        headers={
            "Content-Disposition": f'attachment; filename="{download_name}"'
        },
    )


@router.delete("/jobs/{id}/reports/{report_id}")
async def delete_report(
    id: str,
    report_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(id)
    await _check_job_access(job, user, write=True)
    report = await QCReports.get_report_by_id(report_id)
    if not report or report.job_id != id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    await QCReports.delete_report(report_id)
    return {"status": True}


############################
# Bulk Finding Actions
############################


@router.post("/jobs/{job_id}/findings/bulk")
async def bulk_update_findings(
    job_id: str,
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
):
    """Apply an action to many findings at once.

    Body:
      {
        "finding_ids": [str, ...],
        "action": "confirm|dismiss|delete|severity|merge_duplicate|unlink_duplicate",
        # action-specific extras:
        "severity": "critical|major|minor|info",  # for severity
        "dismissal_reason": str,                   # for dismiss
        "canonical_finding_id": str,               # for merge_duplicate (optional override)
      }
    """
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user, write=True)

    finding_ids = form_data.get("finding_ids") or []
    action = form_data.get("action")
    if not finding_ids or not action:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="finding_ids and action are required",
        )

    updated = 0
    if action == "confirm":
        updated = await QCFindings.bulk_update_fields(job_id, finding_ids, {"status": "confirmed"})
    elif action == "dismiss":
        reason = form_data.get("dismissal_reason")
        # For dismissal reason, update per-finding since meta merge is nuanced.
        updated = 0
        for fid in finding_ids:
            finding = await QCFindings.get_finding_by_id(fid)
            if not finding or finding.job_id != job_id:
                continue
            update_form = QCFindingUpdateForm(
                status="dismissed",
                meta={**(finding.meta or {}), "dismissal_reason": reason} if reason else None,
            )
            await QCFindings.update_finding(fid, update_form)
            updated += 1
    elif action == "severity":
        sev = form_data.get("severity")
        if sev not in ("critical", "major", "minor", "info"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="severity must be one of critical/major/minor/info",
            )
        updated = await QCFindings.bulk_update_fields(job_id, finding_ids, {"severity": sev})
    elif action == "delete":
        updated = 0
        for fid in finding_ids:
            finding = await QCFindings.get_finding_by_id(fid)
            if finding and finding.job_id == job_id:
                await QCFindings.delete_finding(fid)
                updated += 1
    elif action == "merge_duplicate":
        # All finding_ids become duplicates of canonical_finding_id.
        canonical = form_data.get("canonical_finding_id")
        if not canonical:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="canonical_finding_id required for merge_duplicate",
            )
        canon_row = await QCFindings.get_finding_by_id(canonical)
        if not canon_row or canon_row.job_id != job_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="canonical finding not found",
            )
        # Ensure canonical itself is not marked as duplicate
        await QCFindings.set_canonical(canonical, None)
        target_ids = [fid for fid in finding_ids if fid != canonical]
        updated = await QCFindings.bulk_update_fields(
            job_id, target_ids, {"canonical_finding_id": canonical}
        )
    elif action == "unlink_duplicate":
        updated = await QCFindings.bulk_update_fields(
            job_id, finding_ids, {"canonical_finding_id": None}
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown action: {action}",
        )

    return {"status": True, "updated": updated, "action": action}


############################
# Finding Location Editing
############################


@router.post("/jobs/{job_id}/findings/{finding_id}/location")
async def update_finding_location(
    job_id: str,
    finding_id: str,
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
):
    """Update a finding's location. Two modes:

    - `{"location": {x, y, width, height}}` — set explicitly.
    - `{"reference_text": "MT-415AB"}` — snap to actual text position via find_text_on_page.
    """
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user, write=True)

    finding = await QCFindings.get_finding_by_id(finding_id)
    if not finding or finding.job_id != job_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )

    new_location = form_data.get("location")
    ref_text = form_data.get("reference_text")
    source = "manual"

    if ref_text and finding.document_id and finding.page_number:
        try:
            from open_webui.utils.qc_document import find_text_on_page

            doc = await QCJobDocuments.get_document_by_id(finding.document_id)
            if doc:
                file_record = await Files.get_file_by_id(doc.file_id)
                if file_record:
                    pdf_path = Storage.get_file(file_record.path)
                    matches = find_text_on_page(pdf_path, finding.page_number, ref_text)
                    if matches:
                        new_location = matches[0]
                        source = "text_search"
        except Exception as e:
            log.warning(f"Text search for finding {finding_id} failed: {e}")

    if new_location is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a valid `location` or matching `reference_text` is required",
        )

    updated_meta = {
        **(finding.meta or {}),
        "location_source": source,
    }
    if ref_text:
        updated_meta["reference_text"] = ref_text

    updated = await QCFindings.update_finding(
        finding_id,
        QCFindingUpdateForm(location=new_location, meta=updated_meta),
    )
    return updated


############################
# Duplicate Management
############################


@router.get("/jobs/{job_id}/duplicates")
async def get_job_duplicates(
    job_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    """Return duplicate clusters for this job."""
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user)

    findings = await QCFindings.get_findings_by_job_id(job_id)
    clusters: dict[str, dict] = {}
    # Index canonical findings
    by_id = {f.id: f for f in findings}
    for f in findings:
        if f.canonical_finding_id:
            canonical = by_id.get(f.canonical_finding_id)
            if not canonical:
                continue
            c = clusters.setdefault(
                canonical.id,
                {
                    "canonical": canonical.model_dump(),
                    "duplicates": [],
                },
            )
            c["duplicates"].append(f.model_dump())

    # Remove singletons (shouldn't happen but be safe)
    out = [v for v in clusters.values() if v["duplicates"]]
    return {"clusters": out, "count": len(out)}


@router.post("/jobs/{job_id}/duplicates/recompute")
async def recompute_duplicates(
    job_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user, write=True)

    from open_webui.utils.qc_duplicates import find_and_link_duplicates

    # Clear existing canonical links first so recompute is fresh
    findings = await QCFindings.get_findings_by_job_id(job_id)
    linked_ids = [f.id for f in findings if f.canonical_finding_id]
    if linked_ids:
        await QCFindings.bulk_update_fields(job_id, linked_ids, {"canonical_finding_id": None})

    linked = await find_and_link_duplicates(job_id)
    return {"status": True, "duplicates_linked": linked}


############################
# Suppression Rules
############################


async def _check_rule_access(rule, user, write=False):
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if user.role == "admin":
        return
    if rule.user_id == user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
    )


@router.get("/suppression-rules", response_model=list[QCSuppressionRuleModel])
async def list_suppression_rules(
    request: Request,
    scope: Optional[str] = Query(None),
    template_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    if user.role == "admin":
        return await QCSuppressionRules.get_rules(
            scope=scope, template_id=template_id, project_id=project_id
        )
    return await QCSuppressionRules.get_rules(
        user_id=user.id, scope=scope, template_id=template_id, project_id=project_id
    )


@router.post("/suppression-rules", response_model=Optional[QCSuppressionRuleModel])
async def create_suppression_rule(
    request: Request,
    form_data: QCSuppressionRuleForm,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    if form_data.scope not in ("template", "project", "global"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scope must be one of template|project|global",
        )
    if form_data.match_type not in (
        "title_exact",
        "title_regex",
        "title_contains",
        "checklist_item",
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid match_type",
        )
    return await QCSuppressionRules.insert_rule(user.id, form_data)


@router.post(
    "/suppression-rules/{rule_id}", response_model=Optional[QCSuppressionRuleModel]
)
async def update_suppression_rule(
    rule_id: str,
    request: Request,
    form_data: QCSuppressionRuleForm,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    rule = await QCSuppressionRules.get_rule_by_id(rule_id)
    await _check_rule_access(rule, user, write=True)
    return await QCSuppressionRules.update_rule(rule_id, form_data)


@router.delete("/suppression-rules/{rule_id}")
async def delete_suppression_rule(
    rule_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    rule = await QCSuppressionRules.get_rule_by_id(rule_id)
    await _check_rule_access(rule, user, write=True)
    await QCSuppressionRules.delete_rule(rule_id)
    return {"status": True}


@router.get(
    "/jobs/{job_id}/suppression-events",
    response_model=list[QCSuppressionEventModel],
)
async def list_suppression_events(
    job_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user)
    return await QCSuppressionEvents.get_events_by_job_id(job_id)


@router.post(
    "/jobs/{job_id}/findings/{finding_id}/create-suppression-rule",
    response_model=Optional[QCSuppressionRuleModel],
)
async def create_rule_from_finding(
    job_id: str,
    finding_id: str,
    request: Request,
    form_data: Optional[dict] = None,
    user=Depends(get_verified_user),
):
    """Convenience shortcut: create a title_contains rule from a dismissed finding.

    Body (optional):
      { "scope": "template|project|global" (default: "template"),
        "match_type": "...", "match_value": "...", "name": "...", "reason": "..." }
    """
    await _check_qc_access(request, user)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user, write=True)

    finding = await QCFindings.get_finding_by_id(finding_id)
    if not finding or finding.job_id != job_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )

    body = form_data or {}
    scope = body.get("scope", "template")
    if scope not in ("template", "project", "global"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scope must be one of template|project|global",
        )
    match_type = body.get("match_type", "title_contains")
    match_value = body.get("match_value") or (finding.title or "")
    if not match_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="match_value cannot be empty",
        )
    name = body.get("name") or f"Suppress: {(finding.title or '')[:60]}"
    reason = body.get("reason") or (finding.meta or {}).get("dismissal_reason") or ""

    rule_form = QCSuppressionRuleForm(
        scope=scope,
        template_id=job.template_id if scope == "template" else None,
        project_id=job.project_id if scope == "project" else None,
        name=name,
        enabled=1,
        match_type=match_type,
        match_value=match_value,
        reason=reason,
        meta={"created_from_finding": finding_id, "job_id": job_id},
    )
    return await QCSuppressionRules.insert_rule(user.id, rule_form)


############################
# Template Versioning
############################


@router.get(
    "/templates/{id}/versions",
    response_model=list[QCTemplateVersionModel],
)
async def list_template_versions(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    template = await QCTemplates.get_template_by_id(id)
    await _check_template_access(template, user)
    return await QCTemplateVersions.get_versions_by_template_id(id)


@router.get(
    "/templates/{id}/versions/diff",
)
async def diff_template_versions(
    id: str,
    request: Request,
    a: int = Query(...),
    b: int = Query(...),
    user=Depends(get_verified_user),
):
    """Return both versions' content — client diffs them."""
    await _check_qc_access(request, user)
    template = await QCTemplates.get_template_by_id(id)
    await _check_template_access(template, user)

    va = await QCTemplateVersions.get_version_by_number(id, a)
    vb = await QCTemplateVersions.get_version_by_number(id, b)
    if not va or not vb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both versions not found",
        )
    return {"a": va.model_dump(), "b": vb.model_dump()}


@router.get(
    "/templates/{id}/versions/{version_number}",
    response_model=Optional[QCTemplateVersionModel],
)
async def get_template_version(
    id: str,
    version_number: int,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    template = await QCTemplates.get_template_by_id(id)
    await _check_template_access(template, user)
    version = await QCTemplateVersions.get_version_by_number(id, version_number)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )
    return version


@router.post(
    "/templates/{id}/versions/{version_number}/restore",
    response_model=Optional[QCTemplateModel],
)
async def restore_template_version(
    id: str,
    version_number: int,
    request: Request,
    user=Depends(get_verified_user),
):
    """Restore a prior version by creating a new version copying its content.

    The new version's change_source is 'restore' and parent_version_id points
    back to the version being restored. The template is updated in place to
    match that content and current_version_id is pinned to the new version.
    """
    await _check_qc_access(request, user)
    template = await QCTemplates.get_template_by_id(id)
    await _check_template_access(template, user, write=True)

    old = await QCTemplateVersions.get_version_by_number(id, version_number)
    if not old:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )

    restore_form = QCTemplateForm(
        name=old.name or template.name,
        description=old.description if old.description is not None else template.description,
        system_prompt=old.system_prompt,
        model_id=old.model_id,
        meta=old.meta,
    )

    # Determine whether a new version will be created (only if content differs)
    will_change = _would_create_new_version(template, restore_form)
    if not will_change:
        # Content already matches; nothing to do beyond pinning (already the current, since same content)
        return template

    # Force-create a version with change_source='restore' + parent pointing to the restored one
    async with get_async_db_context(None) as db:
        new_version = await QCTemplateVersions.create_version(
            template_id=id,
            user_id=user.id,
            name=restore_form.name,
            description=restore_form.description,
            system_prompt=restore_form.system_prompt,
            model_id=restore_form.model_id,
            meta=restore_form.meta,
            change_summary=f"Restored from v{old.version_number}",
            change_source="restore",
            parent_version_id=old.id,
            db=db,
        )
        # Apply content to the template row and pin
        await db.execute(
            sa_update(QCTemplate).filter_by(id=id).values(
                name=restore_form.name,
                description=restore_form.description,
                system_prompt=restore_form.system_prompt,
                model_id=restore_form.model_id,
                meta=restore_form.meta,
                current_version_id=new_version.id if new_version else template.current_version_id,
                updated_at=int(time.time()),
            )
        )
        await db.commit()
    return await QCTemplates.get_template_by_id(id)


def _would_create_new_version(template: QCTemplateModel, form: QCTemplateForm) -> bool:
    from open_webui.models.qc import _content_fields_changed

    return _content_fields_changed(template, form)


############################
# Test Harness
############################


async def _check_test_set_access(test_set, user, write=False):
    if not test_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if user.role == "admin":
        return
    if test_set.user_id == user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
    )


async def _check_test_run_access(run, user):
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if user.role == "admin":
        return
    if run.user_id == user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
    )


@router.get("/test-sets", response_model=list[QCTestSetModel])
async def list_test_sets(
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    if user.role == "admin":
        return await QCTestSets.get_test_sets()
    return await QCTestSets.get_test_sets(user_id=user.id)


@router.post("/test-sets", response_model=Optional[QCTestSetModel])
async def create_test_set(
    request: Request,
    form_data: QCTestSetForm,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    return await QCTestSets.insert_test_set(user.id, form_data)


@router.get("/test-sets/{id}")
async def get_test_set(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    ts = await QCTestSets.get_test_set_by_id(id)
    await _check_test_set_access(ts, user)
    docs = await QCTestSetDocuments.get_documents_by_test_set_id(id)
    expected = await QCTestSetExpectedFindings.get_expected_by_test_set_id(id)
    return {
        **ts.model_dump(),
        "documents": [d.model_dump() for d in docs],
        "expected_findings": [e.model_dump() for e in expected],
    }


@router.post("/test-sets/{id}", response_model=Optional[QCTestSetModel])
async def update_test_set(
    id: str,
    request: Request,
    form_data: QCTestSetForm,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    ts = await QCTestSets.get_test_set_by_id(id)
    await _check_test_set_access(ts, user, write=True)
    return await QCTestSets.update_test_set(id, form_data)


@router.delete("/test-sets/{id}")
async def delete_test_set(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    ts = await QCTestSets.get_test_set_by_id(id)
    await _check_test_set_access(ts, user, write=True)
    await QCTestSets.delete_test_set(id)
    return {"status": True}


@router.post("/test-sets/{id}/documents/add")
async def add_test_set_document(
    id: str,
    request: Request,
    file: UploadFile = File(...),
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    ts = await QCTestSets.get_test_set_by_id(id)
    await _check_test_set_access(ts, user, write=True)

    from open_webui.utils.qc_document import ingest_file_as_document

    try:
        file_id, page_images, page_count, _size = await ingest_file_as_document(
            user.id,
            file,
            max_upload_bytes=QC_MAX_UPLOAD_BYTES,
            max_pdf_pages=QC_MAX_PDF_PAGES,
            allowed_content_types=ALLOWED_UPLOAD_CONTENT_TYPES,
            allowed_extensions=ALLOWED_UPLOAD_EXTENSIONS,
            extra_meta={"qc_test_set_id": id},
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except OverflowError as oe:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(oe)
        )

    doc = await QCTestSetDocuments.insert_document(
        test_set_id=id,
        file_id=file_id,
        name=file.filename,
        page_count=page_count,
        meta={"page_images": page_images},
    )
    return doc


@router.delete("/test-sets/{id}/documents/{doc_id}")
async def remove_test_set_document(
    id: str,
    doc_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    ts = await QCTestSets.get_test_set_by_id(id)
    await _check_test_set_access(ts, user, write=True)
    await QCTestSetDocuments.delete_document(doc_id)
    return {"status": True}


@router.get(
    "/test-sets/{id}/expected-findings",
    response_model=list[QCTestSetExpectedFindingModel],
)
async def list_expected_findings(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    ts = await QCTestSets.get_test_set_by_id(id)
    await _check_test_set_access(ts, user)
    return await QCTestSetExpectedFindings.get_expected_by_test_set_id(id)


@router.post(
    "/test-sets/{id}/expected-findings",
    response_model=Optional[QCTestSetExpectedFindingModel],
)
async def create_expected_finding(
    id: str,
    request: Request,
    form_data: QCTestSetExpectedFindingForm,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    ts = await QCTestSets.get_test_set_by_id(id)
    await _check_test_set_access(ts, user, write=True)
    return await QCTestSetExpectedFindings.insert_expected(id, form_data)


@router.post(
    "/test-sets/{id}/expected-findings/{ef_id}",
    response_model=Optional[QCTestSetExpectedFindingModel],
)
async def update_expected_finding(
    id: str,
    ef_id: str,
    request: Request,
    form_data: QCTestSetExpectedFindingForm,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    ts = await QCTestSets.get_test_set_by_id(id)
    await _check_test_set_access(ts, user, write=True)
    return await QCTestSetExpectedFindings.update_expected(ef_id, form_data)


@router.delete("/test-sets/{id}/expected-findings/{ef_id}")
async def delete_expected_finding(
    id: str,
    ef_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    ts = await QCTestSets.get_test_set_by_id(id)
    await _check_test_set_access(ts, user, write=True)
    await QCTestSetExpectedFindings.delete_expected(ef_id)
    return {"status": True}


@router.post(
    "/test-sets/{id}/seed-from-job/{job_id}",
)
async def seed_test_set_from_job(
    id: str,
    job_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    """Copy confirmed findings from a job into the test set as expected findings.

    Only findings whose `document_id` maps to a `file_id` already present in this
    test set are copied (matched via `qc_test_set_document.file_id`).
    """
    await _check_qc_access(request, user)
    ts = await QCTestSets.get_test_set_by_id(id)
    await _check_test_set_access(ts, user, write=True)
    job = await QCJobs.get_job_by_id(job_id)
    await _check_job_access(job, user)

    ts_docs = await QCTestSetDocuments.get_documents_by_test_set_id(id)
    # file_id -> test set document id
    ts_doc_by_file_id = {d.file_id: d.id for d in ts_docs}

    job_docs = await QCJobDocuments.get_documents_by_job_id(job_id)
    # job document id -> file_id
    job_doc_file_ids = {d.id: d.file_id for d in job_docs}

    findings = await QCFindings.get_findings_by_job_id(job_id) or []
    seeded = 0
    for f in findings:
        if f.status != "confirmed":
            continue
        file_id = job_doc_file_ids.get(f.document_id) if f.document_id else None
        if not file_id:
            continue
        ts_doc_id = ts_doc_by_file_id.get(file_id)
        if not ts_doc_id:
            continue
        form = QCTestSetExpectedFindingForm(
            document_id=ts_doc_id,
            page_number=f.page_number,
            checklist_item_id=f.checklist_item_id,
            severity=f.severity,
            title=f.title,
            description=f.description,
            location=f.location if isinstance(f.location, dict) else None,
            match_title_patterns=None,
            seeded_from_finding_id=f.id,
        )
        await QCTestSetExpectedFindings.insert_expected(id, form)
        seeded += 1
    return {"status": True, "seeded": seeded}


@router.post("/test-sets/{id}/run", response_model=Optional[QCTestRunModel])
async def run_test_set(
    id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    form_data: dict,
    user=Depends(get_verified_user),
):
    """Run a test set against a template. Creates a shadow QC job that will trigger
    metric computation when it finishes.
    """
    await _check_qc_access(request, user)
    ts = await QCTestSets.get_test_set_by_id(id)
    await _check_test_set_access(ts, user)

    template_id = form_data.get("template_id")
    if not template_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="template_id required",
        )
    template = await QCTemplates.get_template_by_id(template_id)
    await _check_template_access(template, user)

    template_version_id = form_data.get("template_version_id") or template.current_version_id
    pinned_version = None
    if template_version_id:
        pinned_version = await QCTemplateVersions.get_version_by_id(template_version_id)
        if pinned_version and pinned_version.template_id != template.id:
            pinned_version = None

    source_system_prompt = (
        pinned_version.system_prompt if pinned_version else template.system_prompt
    )
    source_model_id = form_data.get("model_id_override") or (
        pinned_version.model_id if pinned_version else template.model_id
    )
    source_meta = (pinned_version.meta if pinned_version else template.meta) or {}

    if not source_model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No model resolved for this template",
        )

    # Create the test run row first so we can point the shadow job at it.
    test_run = await QCTestRuns.insert_run(
        user_id=user.id,
        test_set_id=id,
        template_id=template.id,
        template_version_id=pinned_version.id if pinned_version else None,
        meta={"model_id_override": form_data.get("model_id_override")},
    )
    if not test_run:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create test run",
        )

    # Build the shadow job meta (carry KB context similarly to create_job)
    job_meta = {
        "checklist_snapshot": source_meta.get("checklist", []),
        "knowledge_base_ids": source_meta.get("knowledge_base_ids", []),
        "is_test_run": True,
        "test_run_id": test_run.id,
    }
    xref_config = source_meta.get("cross_reference_analysis")
    if xref_config:
        job_meta["cross_reference_analysis"] = xref_config

    # Fetch KB context (same logic as create_job, abbreviated)
    kb_ids = source_meta.get("knowledge_base_ids", [])
    if kb_ids:
        kb_parts = []
        for kb_id in kb_ids:
            try:
                kb_files = await Knowledges.get_files_by_id(kb_id)
                for f in kb_files:
                    file_content = (f.data or {}).get("content", "")
                    if file_content:
                        file_name = (f.meta or {}).get("name", f.filename)
                        kb_parts.append(f"=== {file_name} ===\n{file_content}")
            except Exception as e:
                log.warning(f"Failed to fetch KB {kb_id} content: {e}")
        kb_context = "\n\n".join(kb_parts)
        max_kb_chars = 500_000
        if len(kb_context) > max_kb_chars:
            kb_context = kb_context[:max_kb_chars]
            job_meta["kb_truncated"] = True
        if kb_context:
            job_meta["kb_context"] = kb_context

    shadow_job = await QCJobs.insert_new_job(
        user.id,
        QCJobForm(
            name=f"[Test] {ts.name}",
            template_id=template.id,
            template_version_id=pinned_version.id if pinned_version else None,
            model_id=source_model_id,
            system_prompt=source_system_prompt,
            test_run_id=test_run.id,
            meta=job_meta,
        ),
    )
    if not shadow_job:
        await QCTestRuns.update_run(test_run.id, status="failed", meta={"error": "Failed to create shadow job"})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create shadow job",
        )

    # Copy test-set documents into qc_job_document (share same file_id + page_images).
    ts_docs = await QCTestSetDocuments.get_documents_by_test_set_id(id)
    if not ts_docs:
        await QCTestRuns.update_run(test_run.id, status="failed", meta={"error": "Test set has no documents"})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test set has no documents",
        )
    for td in ts_docs:
        job_doc = await QCJobDocuments.insert_document(
            shadow_job.id,
            QCJobDocumentForm(file_id=td.file_id, document_type="subject"),
        )
        await QCJobDocuments.update_document(
            job_doc.id,
            page_count=td.page_count,
            status="pending",
            meta={"page_images": (td.meta or {}).get("page_images", {})},
        )

    await QCTestRuns.update_run(
        test_run.id,
        status="running",
        shadow_job_id=shadow_job.id,
    )

    from open_webui.utils.qc_analysis import run_qc_job

    background_tasks.add_task(run_qc_job, request, shadow_job.id, user)
    await QCJobs.update_job_status(shadow_job.id, "running")

    return await QCTestRuns.get_run_by_id(test_run.id)


@router.get("/test-runs", response_model=list[QCTestRunModel])
async def list_test_runs(
    request: Request,
    test_set_id: Optional[str] = Query(None),
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    if user.role == "admin":
        return await QCTestRuns.get_runs(test_set_id=test_set_id)
    return await QCTestRuns.get_runs(user_id=user.id, test_set_id=test_set_id)


@router.get("/test-runs/{id}")
async def get_test_run(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    await _check_qc_access(request, user)
    run = await QCTestRuns.get_run_by_id(id)
    await _check_test_run_access(run, user)
    test_set = await QCTestSets.get_test_set_by_id(run.test_set_id)
    return {**run.model_dump(), "test_set": test_set.model_dump() if test_set else None}
