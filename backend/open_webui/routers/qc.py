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
from sqlalchemy.orm import Session

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
)
from open_webui.models.files import Files, FileForm
from open_webui.models.knowledge import Knowledges
from open_webui.models.access_grants import AccessGrants
from open_webui.storage.provider import Storage

from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import has_permission
from open_webui.internal.db import get_session
from open_webui.constants import ERROR_MESSAGES

log = logging.getLogger(__name__)

router = APIRouter()


############################
# Helpers
############################


def _check_qc_access(request, user):
    """Check if user has QC access permission."""
    if user.role != "admin" and not has_permission(
        user.id,
        "features.qc",
        request.app.state.config.USER_PERMISSIONS,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


def _check_job_access(job, user, write=False):
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
    if AccessGrants.has_access(
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


def _check_template_access(template, user, write=False):
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
    if AccessGrants.has_access(
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


############################
# Template Endpoints
############################


@router.get("/templates", response_model=list[QCTemplateModel])
async def get_templates(
    request: Request,
    user=Depends(get_verified_user),
):
    _check_qc_access(request, user)
    templates = QCTemplates.get_templates()
    if user.role == "admin":
        return templates
    # Filter to templates user owns or has access to
    return [
        t
        for t in templates
        if t.user_id == user.id
        or AccessGrants.has_access(
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
    _check_qc_access(request, user)
    template = QCTemplates.get_template_by_id(id)
    _check_template_access(template, user)
    return template


@router.post("/templates", response_model=Optional[QCTemplateModel])
async def create_template(
    request: Request,
    form_data: QCTemplateForm,
    user=Depends(get_verified_user),
):
    _check_qc_access(request, user)
    template = QCTemplates.insert_new_template(user.id, form_data)
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
    user=Depends(get_verified_user),
):
    _check_qc_access(request, user)
    template = QCTemplates.get_template_by_id(id)
    _check_template_access(template, user, write=True)
    updated = QCTemplates.update_template_by_id(id, form_data)
    return updated


@router.delete("/templates/{id}")
async def delete_template(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    _check_qc_access(request, user)
    template = QCTemplates.get_template_by_id(id)
    _check_template_access(template, user, write=True)
    QCTemplates.delete_template_by_id(id)
    return {"status": True}


@router.post("/templates/{id}/clone", response_model=Optional[QCTemplateModel])
async def clone_template(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    _check_qc_access(request, user)
    template = QCTemplates.get_template_by_id(id)
    _check_template_access(template, user)

    clone_form = QCTemplateForm(
        name=f"{template.name} (Copy)",
        description=template.description,
        system_prompt=template.system_prompt,
        model_id=template.model_id,
        meta=template.meta,
    )
    return QCTemplates.insert_new_template(user.id, clone_form)


############################
# Job Endpoints
############################


@router.get("/jobs", response_model=list[QCJobModel])
async def get_jobs(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    user=Depends(get_verified_user),
):
    _check_qc_access(request, user)
    if user.role == "admin":
        jobs = QCJobs.get_jobs(status=status_filter)
    else:
        jobs = QCJobs.get_jobs(user_id=user.id, status=status_filter)
    return jobs


@router.get("/jobs/{id}", response_model=Optional[QCJobModel])
async def get_job_by_id(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(id)
    _check_job_access(job, user)
    return job


@router.post("/jobs", response_model=Optional[QCJobModel])
async def create_job(
    request: Request,
    form_data: QCJobForm,
    user=Depends(get_verified_user),
):
    _check_qc_access(request, user)

    # If template_id provided, snapshot template settings
    if form_data.template_id:
        template = QCTemplates.get_template_by_id(form_data.template_id)
        if template:
            if not form_data.model_id:
                form_data.model_id = template.model_id
            if not form_data.system_prompt:
                form_data.system_prompt = template.system_prompt
            # Snapshot checklist into job meta
            template_meta = template.meta or {}
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
                        kb_files = Knowledges.get_files_by_id(kb_id)
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
                if len(kb_context) > max_kb_chars:
                    log.warning(
                        f"KB context truncated from {len(kb_context)} to {max_kb_chars} chars"
                    )
                    kb_context = kb_context[:max_kb_chars]
                if kb_context:
                    job_meta["kb_context"] = kb_context

            form_data.meta = job_meta

    job = QCJobs.insert_new_job(user.id, form_data)
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
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(id)
    _check_job_access(job, user, write=True)
    return QCJobs.update_job_by_id(id, form_data)


@router.delete("/jobs/{id}")
async def delete_job(
    id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(id)
    _check_job_access(job, user, write=True)
    QCJobs.delete_job_by_id(id)
    return {"status": True}


@router.post("/jobs/{id}/run")
async def run_job(
    id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user=Depends(get_verified_user),
):
    """Start QC analysis for a job. Runs in background."""
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(id)
    _check_job_access(job, user, write=True)

    if job.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is already running",
        )

    if not job.model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No model selected for this job",
        )

    # Check documents exist
    documents = QCJobDocuments.get_documents_by_job_id(id)
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No documents uploaded for this job",
        )

    from open_webui.utils.qc_analysis import run_qc_job

    background_tasks.add_task(run_qc_job, request, id, user)
    QCJobs.update_job_status(id, "running")

    return {"status": True, "message": "QC analysis started"}


@router.post("/jobs/{job_id}/self-improve")
async def self_improve_template(
    job_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    """Analyze reviewed findings and suggest improvements to the source template."""
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(job_id)
    _check_job_access(job, user)

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

    template = QCTemplates.get_template_by_id(job.template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source template no longer exists",
        )

    _check_template_access(template, user, write=True)

    findings = QCFindings.get_findings_by_job_id(job_id)
    has_reviewed = any(f.status in ("confirmed", "dismissed") for f in findings)
    if not has_reviewed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one finding must be confirmed or dismissed",
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
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(id)
    _check_job_access(job, user)

    findings = QCFindings.get_findings_by_job_id(id)
    documents = QCJobDocuments.get_documents_by_job_id(id)

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
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(job_id)
    _check_job_access(job, user, write=True)

    if job.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add documents while job is running",
        )

    # Upload the original file
    file_id = str(uuid.uuid4())
    filename = file.filename or "upload"
    storage_filename = f"{file_id}_{filename}"

    contents, file_path = Storage.upload_file(
        file.file,
        storage_filename,
        {
            "OpenWebUI-User-Id": user.id,
            "OpenWebUI-File-Id": file_id,
        },
    )

    content_type = file.content_type or ""

    # Save file record
    Files.insert_new_file(
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
    doc = QCJobDocuments.insert_document(job_id, doc_form)

    # Convert to page images
    page_images = {}

    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        from open_webui.utils.qc_document import convert_pdf_to_pages

        actual_file_path = Storage.get_file(file_path)
        pages = convert_pdf_to_pages(actual_file_path)

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

            Files.insert_new_file(
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

        QCJobDocuments.update_document(
            doc.id,
            page_count=len(pages),
            status="pending",
            meta={"page_images": page_images},
        )
    elif content_type and content_type.startswith("image/"):
        # Single image - treat as page 1
        page_images["1"] = file_id
        QCJobDocuments.update_document(
            doc.id,
            page_count=1,
            status="pending",
            meta={"page_images": page_images},
        )
    else:
        # Non-visual document (Excel, DOCX, etc.) - mark as pending for text analysis
        QCJobDocuments.update_document(
            doc.id,
            page_count=0,
            status="pending",
            meta={"page_images": {}},
        )

    return QCJobDocuments.get_document_by_id(doc.id)


@router.get("/jobs/{job_id}/documents", response_model=list[QCJobDocumentModel])
async def get_documents(
    job_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(job_id)
    _check_job_access(job, user)
    return QCJobDocuments.get_documents_by_job_id(job_id)


@router.delete("/jobs/{job_id}/documents/{doc_id}")
async def remove_document(
    job_id: str,
    doc_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(job_id)
    _check_job_access(job, user, write=True)

    if job.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove documents while job is running",
        )

    QCJobDocuments.delete_document(doc_id)
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
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(job_id)
    _check_job_access(job, user)

    doc = QCJobDocuments.get_document_by_id(doc_id)
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

    file_record = Files.get_file_by_id(file_id)
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
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(job_id)
    _check_job_access(job, user)

    return QCFindings.get_findings_by_job_id(
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
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(job_id)
    _check_job_access(job, user, write=True)

    finding = QCFindings.insert_finding(user.id, job_id, form_data)
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
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(job_id)
    _check_job_access(job, user, write=True)

    finding = QCFindings.get_finding_by_id(finding_id)
    if not finding or finding.job_id != job_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )

    return QCFindings.update_finding(finding_id, form_data)


@router.delete("/jobs/{job_id}/findings/{finding_id}")
async def delete_finding(
    job_id: str,
    finding_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(job_id)
    _check_job_access(job, user, write=True)

    finding = QCFindings.get_finding_by_id(finding_id)
    if not finding or finding.job_id != job_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )

    QCFindings.delete_finding(finding_id)
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
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(job_id)
    _check_job_access(job, user)

    return QCComments.get_comments_by_finding_id(finding_id)


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
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(job_id)
    _check_job_access(job, user)

    finding = QCFindings.get_finding_by_id(finding_id)
    if not finding or finding.job_id != job_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )

    return QCComments.insert_comment(user.id, finding_id, job_id, form_data)


@router.delete("/jobs/{job_id}/findings/{finding_id}/comments/{comment_id}")
async def delete_comment(
    job_id: str,
    finding_id: str,
    comment_id: str,
    request: Request,
    user=Depends(get_verified_user),
):
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(job_id)
    _check_job_access(job, user, write=True)

    comment = QCComments.get_comment_by_id(comment_id)
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

    QCComments.delete_comment(comment_id)
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
    _check_qc_access(request, user)
    job = QCJobs.get_job_by_id(job_id)
    _check_job_access(job, user)

    meta = job.meta or {}
    checklist = meta.get("checklist_snapshot", [])
    findings = QCFindings.get_findings_by_job_id(job_id)

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
