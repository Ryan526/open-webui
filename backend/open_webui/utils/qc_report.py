"""PDF report generation for QC jobs (branded PDF + redlined PDF)."""

import base64
import io
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from open_webui.models.files import Files, FileForm
from open_webui.models.qc import (
    QCJobModel,
    QCJobDocumentModel,
    QCFindingModel,
)
from open_webui.storage.provider import Storage

log = logging.getLogger(__name__)


SEVERITY_ORDER = ["critical", "major", "minor", "info"]

DEFAULT_BRANDING = {
    "primary_color": "#1a1a1a",
    "client_name": "",
    "project_number": "",
    "footer": "",
    "logo_file_id": None,
}

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "qc_report_templates")


def _resolve_branding(job: Optional[dict], template_meta: Optional[dict]) -> dict:
    """Merge job-level branding overrides onto template branding."""
    b: dict = dict(DEFAULT_BRANDING)
    tpl = (template_meta or {}).get("branding") or {}
    for k, v in tpl.items():
        if v is not None:
            b[k] = v
    job_b = (job or {}).get("branding") or {}
    for k, v in job_b.items():
        if v is not None:
            b[k] = v
    return b


def _logo_data_uri(logo_file_id: Optional[str]) -> Optional[str]:
    if not logo_file_id:
        return None
    try:
        file_record = Files.get_file_by_id(logo_file_id)
        if not file_record:
            return None
        path = Storage.get_file(file_record.path)
        with open(path, "rb") as f:
            data = f.read()
        ext = (os.path.splitext(file_record.filename or "")[1] or ".png").lstrip(".").lower()
        mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}
        mime = mime_map.get(ext, "image/png")
        return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
    except Exception as e:
        log.warning(f"Could not load logo {logo_file_id}: {e}")
        return None


def _crop_finding(
    annotated_png_bytes: bytes,
    location: Optional[dict],
    pad_ratio: float = 0.05,
) -> Optional[bytes]:
    """Crop the finding region (with padding) from an annotated page PNG."""
    if not annotated_png_bytes:
        return None
    try:
        from PIL import Image
    except ImportError:
        return annotated_png_bytes
    try:
        img = Image.open(io.BytesIO(annotated_png_bytes)).convert("RGB")
    except Exception:
        return None

    w, h = img.size
    if not location or not isinstance(location, dict):
        return annotated_png_bytes
    try:
        x = float(location.get("x", 0))
        y = float(location.get("y", 0))
        lw = float(location.get("width", 0))
        lh = float(location.get("height", 0))
    except (TypeError, ValueError):
        return annotated_png_bytes

    if lw <= 0 or lh <= 0:
        return annotated_png_bytes

    pad_x = max(lw * pad_ratio, 0.02)
    pad_y = max(lh * pad_ratio, 0.02)
    x0 = max(0.0, x - pad_x)
    y0 = max(0.0, y - pad_y)
    x1 = min(1.0, x + lw + pad_x)
    y1 = min(1.0, y + lh + pad_y)

    crop = img.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
    buf = io.BytesIO()
    crop.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _image_bytes_to_data_uri(img_bytes: Optional[bytes]) -> Optional[str]:
    if not img_bytes:
        return None
    return f"data:image/png;base64,{base64.b64encode(img_bytes).decode('ascii')}"


def _load_annotated_image(doc_meta: dict, page_number: Optional[int]) -> Optional[bytes]:
    if not page_number:
        return None
    annotated = (doc_meta or {}).get("annotated_images") or {}
    page_images = (doc_meta or {}).get("page_images") or {}
    file_id = annotated.get(str(page_number)) or page_images.get(str(page_number))
    if not file_id:
        return None
    try:
        file_record = Files.get_file_by_id(file_id)
        if not file_record:
            return None
        path = Storage.get_file(file_record.path)
        with open(path, "rb") as f:
            return f.read()
    except Exception as e:
        log.warning(f"Could not load annotated image file {file_id}: {e}")
        return None


def _render_branded_html(context: dict) -> str:
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except ImportError:
        log.error("jinja2 not installed; cannot render branded report")
        raise

    env = Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template("branded_report.html")
    return tpl.render(**context)


def generate_branded_pdf(
    job: QCJobModel,
    documents: list[QCJobDocumentModel],
    findings: list[QCFindingModel],
    *,
    branding: Optional[dict] = None,
    include_severities: Optional[list[str]] = None,
    include_dismissed: bool = False,
) -> tuple[bytes, dict]:
    """Produce a branded PDF report using PyMuPDF's Story engine.

    Returns (pdf_bytes, meta) where meta contains warnings/options used.
    """
    try:
        import fitz
    except ImportError:
        raise RuntimeError("PyMuPDF (fitz) is required for branded reports")

    branding = branding or {}
    resolved = dict(DEFAULT_BRANDING)
    for k, v in branding.items():
        if v is not None:
            resolved[k] = v
    resolved["logo_data_uri"] = _logo_data_uri(resolved.get("logo_file_id"))

    warnings: list[str] = []
    include_set = set(s.lower() for s in (include_severities or SEVERITY_ORDER))

    docs_by_id = {d.id: d for d in documents}

    filtered: list[dict] = []
    severity_counts: dict[str, int] = {s: 0 for s in SEVERITY_ORDER}

    for f in findings:
        sev = (f.severity or "info").lower()
        if sev not in include_set:
            continue
        if not include_dismissed and f.status == "dismissed":
            continue
        doc = docs_by_id.get(f.document_id) if f.document_id else None
        doc_name = None
        annotated_bytes: Optional[bytes] = None
        if doc:
            doc_meta = doc.meta or {}
            doc_name = doc_meta.get("name") or doc_meta.get("filename") or doc.file_id
            annotated_bytes = _load_annotated_image(doc_meta, f.page_number)
        cropped = _crop_finding(annotated_bytes, f.location) if annotated_bytes else None
        image_uri = _image_bytes_to_data_uri(cropped)
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        filtered.append(
            {
                "id": f.id,
                "finding_number": f.finding_number,
                "severity": sev,
                "status": f.status,
                "title": f.title,
                "description": f.description,
                "page_number": f.page_number,
                "document_name": doc_name,
                "revision_state": f.revision_state,
                "image_data_uri": image_uri,
            }
        )

    findings_by_severity: dict[str, list[dict]] = {s: [] for s in SEVERITY_ORDER}
    for f in filtered:
        findings_by_severity[f["severity"]].append(f)

    context = {
        "job": {
            "name": job.name,
            "revision_label": job.revision_label,
        },
        "branding": resolved,
        "documents": [d.model_dump() for d in documents],
        "findings": filtered,
        "findings_by_severity": findings_by_severity,
        "severity_order": SEVERITY_ORDER,
        "severity_counts": severity_counts,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    html = _render_branded_html(context)

    # Render to PDF via fitz.Story
    try:
        story = fitz.Story(html=html)
    except Exception as e:
        log.error(f"fitz.Story init failed: {e}")
        raise

    buf = io.BytesIO()
    writer = fitz.DocumentWriter(buf)
    more = 1
    # Letter size at 72 DPI: 612 x 792; margin 48pt
    mediabox = fitz.Rect(0, 0, 612, 792)
    where = fitz.Rect(48, 48, 564, 744)
    while more:
        dev = writer.begin_page(mediabox)
        more, _filled = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()

    pdf_bytes = buf.getvalue()
    meta = {
        "options": {
            "include_severities": sorted(list(include_set)),
            "include_dismissed": include_dismissed,
        },
        "warnings": warnings,
        "severity_counts": severity_counts,
        "findings_included": len(filtered),
    }
    return pdf_bytes, meta


SEVERITY_COLOR_RGB = {
    "critical": (0.86, 0.15, 0.15),
    "major": (0.92, 0.35, 0.05),
    "minor": (0.79, 0.54, 0.02),
    "info": (0.15, 0.39, 0.92),
}


def generate_redlined_pdf(
    job: QCJobModel,
    document: QCJobDocumentModel,
    findings_for_document: list[QCFindingModel],
) -> tuple[bytes, dict]:
    """Produce a redlined copy of the original document PDF with annotations.

    Preserves the existing text layer; only adds annotation objects.
    """
    try:
        import fitz
    except ImportError:
        raise RuntimeError("PyMuPDF (fitz) is required for redlined reports")

    warnings: list[str] = []

    file_record = Files.get_file_by_id(document.file_id)
    if not file_record:
        raise RuntimeError("Source file for document not found")

    path = Storage.get_file(file_record.path)
    name = (file_record.meta or {}).get("name", "") or (file_record.filename or "")

    if not name.lower().endswith(".pdf"):
        raise RuntimeError("Redlined PDF export only supports PDF source documents")

    with open(path, "rb") as f:
        src_bytes = f.read()

    pdf = fitz.open(stream=src_bytes, filetype="pdf")

    # Check if any page has a text layer (best-effort warning)
    has_text_layer = False
    try:
        for p in pdf:
            if (p.get_text("text") or "").strip():
                has_text_layer = True
                break
    except Exception:
        has_text_layer = False
    if not has_text_layer:
        warnings.append(
            "Source PDF has no text layer (image-only). Annotations still applied; text will not be selectable in redlined copy."
        )

    annotated_count = 0
    for f in findings_for_document:
        if not f.page_number or f.page_number < 1 or f.page_number > len(pdf):
            continue
        loc = f.location if isinstance(f.location, dict) else None
        page = pdf.load_page(f.page_number - 1)
        page_rect = page.rect
        pw = page_rect.width
        ph = page_rect.height

        severity = (f.severity or "info").lower()
        color = SEVERITY_COLOR_RGB.get(severity, SEVERITY_COLOR_RGB["info"])

        content_text = f"#{f.finding_number} [{severity.upper()}] {f.title}\n{f.description or ''}".strip()
        title = f"QC Finding #{f.finding_number}"

        if loc:
            try:
                x0 = float(loc.get("x", 0)) * pw
                y0 = float(loc.get("y", 0)) * ph
                w = float(loc.get("width", 0)) * pw
                h = float(loc.get("height", 0)) * ph
            except (TypeError, ValueError):
                x0 = y0 = w = h = 0
            if w > 0 and h > 0:
                rect = fitz.Rect(x0, y0, x0 + w, y0 + h)
                try:
                    annot = page.add_rect_annot(rect)
                    annot.set_colors(stroke=color)
                    annot.set_border(width=2)
                    annot.set_info(title=title, content=content_text)
                    annot.update()
                    annotated_count += 1
                    continue
                except Exception as e:
                    warnings.append(f"Rect annotation failed on page {f.page_number}: {e}")

        # Fallback: text note in top-left of page
        try:
            point = fitz.Point(24, 24 + annotated_count * 14)
            note = page.add_text_annot(point, content_text, icon="Note")
            note.set_colors(stroke=color)
            note.set_info(title=title, content=content_text)
            note.update()
            annotated_count += 1
        except Exception as e:
            warnings.append(f"Text note fallback failed on page {f.page_number}: {e}")

    out_buf = io.BytesIO()
    pdf.save(out_buf, garbage=3, deflate=True)
    pdf.close()

    meta = {
        "document_id": document.id,
        "source_file_id": document.file_id,
        "annotated_count": annotated_count,
        "findings_total": len(findings_for_document),
        "warnings": warnings,
        "has_text_layer": has_text_layer,
    }
    return out_buf.getvalue(), meta


def persist_report_bytes(
    user_id: str,
    job_id: str,
    filename: str,
    data: bytes,
    content_type: str = "application/pdf",
) -> str:
    """Upload report bytes to storage + create a file record. Returns file_id."""
    file_id = str(uuid.uuid4())
    storage_filename = f"{file_id}_{filename}"
    from io import BytesIO as _BytesIO

    contents, file_path = Storage.upload_file(
        _BytesIO(data),
        storage_filename,
        {
            "OpenWebUI-User-Id": user_id,
            "OpenWebUI-File-Id": file_id,
        },
    )
    Files.insert_new_file(
        user_id,
        FileForm(
            id=file_id,
            filename=storage_filename,
            path=file_path,
            meta={
                "name": filename,
                "content_type": content_type,
                "size": len(contents),
                "qc_job_id": job_id,
                "qc_report": True,
            },
        ),
    )
    return file_id
