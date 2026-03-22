import json
import logging
import time
import uuid
from typing import Any, Optional

from open_webui.utils.qc_document import (
    convert_pdf_to_pages,
    render_annotated_page,
    image_to_base64,
    find_text_on_page,
)

log = logging.getLogger(__name__)

QC_SYSTEM_PROMPT = """You are a QC analyst reviewing document pages for quality control issues. Analyze the provided document page image and return findings in valid JSON format only.

Return your response as a JSON object with this exact structure:
{
  "findings": [
    {
      "title": "Brief description of the issue",
      "description": "Detailed explanation of why this is an issue",
      "severity": "critical|major|minor|info",
      "location": {"x": 0.45, "y": 0.30, "width": 0.10, "height": 0.05},
      "reference_text": "MT-415AB",
      "checklist_item_id": null,
      "reasoning": "Why this is an issue based on the standards"
    }
  ],
  "page_summary": "Overall assessment of this page",
  "page_result": "pass|fail|flagged"
}

Location coordinates are normalized (0-1) relative to the page dimensions:
- x, y = top-left corner of the region of interest
- width, height = size of the region — use tight bounding boxes that closely fit the area of concern

reference_text: The exact text label or identifier visible on the drawing near the issue (e.g., "MT-415AB", "Panel LP-2", "20A/1P"). Copy the characters exactly as they appear on the drawing. This is used to precisely locate the finding via text search. If there is no nearby text label, set to null.

If no issues are found, return an empty findings array with page_result "pass".
Return ONLY valid JSON, no markdown code blocks or other text."""


def build_qc_prompt(
    template_system_prompt: Optional[str] = None,
    checklist: Optional[list[dict]] = None,
    kb_context: Optional[str] = None,
) -> str:
    """Construct the full system prompt for QC analysis."""
    parts = [QC_SYSTEM_PROMPT]

    if template_system_prompt:
        parts.append(f"\n--- Custom Instructions ---\n{template_system_prompt}")

    if kb_context:
        parts.append(f"\n--- Reference Standards/Specifications ---\n{kb_context}")

    if checklist:
        checklist_text = "\n--- Checklist Criteria ---\nEvaluate the page against these criteria:\n"
        for item in checklist:
            severity = item.get("severity", "info")
            label = item.get("label", "")
            desc = item.get("description", "")
            checklist_text += f"- [{severity.upper()}] {label}: {desc}\n"
            if item.get("id"):
                checklist_text += f"  (checklist_item_id: {item['id']})\n"
        parts.append(checklist_text)

    return "\n".join(parts)


async def analyze_page(
    request: Any,
    model_id: str,
    system_prompt: str,
    page_image_b64: str,
    page_number: int,
    user: Any,
) -> dict:
    """
    Send a page image to the vision model for QC analysis.
    Returns parsed response dict with findings, page_summary, page_result.
    """
    from open_webui.utils.chat import generate_chat_completion

    form_data = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": page_image_b64},
                    },
                    {
                        "type": "text",
                        "text": f"Analyze page {page_number} of this document for quality control issues. Return your findings as JSON.",
                    },
                ],
            },
        ],
        "stream": False,
        "metadata": {
            "task": "qc_analysis",
            "task_body": f"QC analysis of page {page_number}",
        },
    }

    try:
        response = await generate_chat_completion(
            request,
            form_data,
            user=user,
            bypass_filter=True,
        )

        # Handle response - could be a dict or a StreamingResponse
        if hasattr(response, "body"):
            body = b""
            async for chunk in response.body_iterator:
                if isinstance(chunk, bytes):
                    body += chunk
                else:
                    body += chunk.encode()
            response_data = json.loads(body)
        elif isinstance(response, dict):
            response_data = response
        else:
            response_data = json.loads(response)

        # Extract content from the response
        content = ""
        if "choices" in response_data and response_data["choices"]:
            message = response_data["choices"][0].get("message", {})
            content = message.get("content", "")
        elif "message" in response_data:
            content = response_data["message"].get("content", "")

        return parse_ai_response(content)

    except Exception as e:
        log.error(f"Error analyzing page {page_number}: {e}")
        return {
            "findings": [
                {
                    "title": "Analysis Error",
                    "description": f"Failed to analyze this page: {str(e)}",
                    "severity": "info",
                    "location": None,
                    "checklist_item_id": None,
                    "reasoning": str(e),
                }
            ],
            "page_summary": f"Analysis failed: {str(e)}",
            "page_result": "flagged",
        }


def parse_ai_response(content: str) -> dict:
    """Parse AI response content into structured findings."""
    # Try to extract JSON from the response
    content = content.strip()

    # Remove markdown code blocks if present
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first and last lines (``` markers)
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines)

    try:
        result = json.loads(content)
        if "findings" in result:
            # Validate findings structure
            for finding in result["findings"]:
                if "location" in finding and finding["location"]:
                    loc = finding["location"]
                    # Clamp coordinates to 0-1 range
                    for key in ["x", "y", "width", "height"]:
                        if key in loc:
                            loc[key] = max(0.0, min(1.0, float(loc[key])))
                # Ensure reference_text is a string or None
                ref = finding.get("reference_text")
                if ref is not None and not isinstance(ref, str):
                    finding["reference_text"] = str(ref)
                elif ref is None:
                    finding["reference_text"] = None
            return result
    except json.JSONDecodeError:
        pass

    # Fallback: treat entire content as a single freeform finding
    return {
        "findings": [
            {
                "title": "AI Analysis Result",
                "description": content[:2000],
                "severity": "info",
                "location": None,
                "checklist_item_id": None,
                "reasoning": "Could not parse structured response",
            }
        ],
        "page_summary": content[:500],
        "page_result": "flagged",
    }


SELF_IMPROVE_SYSTEM_PROMPT = """You are a QC template optimization assistant. You analyze feedback from QC reviews to suggest improvements to QC templates.

You will receive:
1. The current template system prompt
2. The current checklist criteria
3. Confirmed findings — real issues the AI correctly identified
4. Dismissed findings with reasons — false positives that should be avoided

Your task is to suggest changes to the system prompt and checklist that would:
- Reduce false positives (based on dismissed findings and their reasons)
- Reinforce patterns that correctly identified real issues
- Add new checklist items if review feedback suggests gaps

Return your response as a JSON object with this exact structure:
{
  "summary": "Brief overall assessment of the review feedback and suggested improvements",
  "system_prompt_changes": [
    { "action": "append", "text": "Text to add to the system prompt", "reason": "Why this addition helps" },
    { "action": "replace", "original": "Exact text to find", "replacement": "New text to use instead", "reason": "Why this replacement helps" },
    { "action": "remove", "text": "Exact text to remove", "reason": "Why removing this helps" }
  ],
  "checklist_changes": [
    { "action": "add", "item": { "label": "New item label", "description": "What to check", "severity": "critical|major|minor|info" }, "reason": "Why this item should be added" },
    { "action": "modify", "item_id": "id-of-existing-item", "updates": { "label": "Updated label", "description": "Updated description", "severity": "updated-severity" }, "reason": "Why this modification helps" },
    { "action": "remove", "item_id": "id-of-item-to-remove", "reason": "Why this item should be removed" }
  ]
}

Guidelines:
- Only suggest changes that are clearly supported by the review feedback
- Be conservative — prefer fewer, high-confidence suggestions over many speculative ones
- For system_prompt replacements, use exact text that can be found in the current prompt
- Include clear reasons for each suggestion
- If no changes are needed for a category, return an empty array
- Return ONLY valid JSON, no markdown code blocks or other text"""


async def generate_self_improve_suggestions(
    request: Any,
    job: Any,
    template: Any,
    findings: list,
    user: Any,
) -> dict:
    """
    Analyze reviewed findings and suggest improvements to the QC template.
    Returns a dict with summary, system_prompt_changes, and checklist_changes.
    """
    from open_webui.utils.chat import generate_chat_completion

    # Build context from findings
    confirmed = [f for f in findings if f.status == "confirmed"]
    dismissed = [f for f in findings if f.status == "dismissed"]

    confirmed_text = ""
    if confirmed:
        confirmed_text = "\n--- Confirmed Findings (Real Issues) ---\n"
        for f in confirmed:
            confirmed_text += f"- [{f.severity.upper()}] {f.title}: {f.description or 'No description'}\n"

    dismissed_text = ""
    if dismissed:
        dismissed_text = "\n--- Dismissed Findings (False Positives) ---\n"
        for f in dismissed:
            reason = (f.meta or {}).get("dismissal_reason", "No reason given")
            dismissed_text += f"- [{f.severity.upper()}] {f.title}: {f.description or 'No description'}\n  Dismissal reason: {reason}\n"

    # Build checklist text
    template_meta = template.meta or {}
    checklist = template_meta.get("checklist", [])
    checklist_text = ""
    if checklist:
        checklist_text = "\n--- Current Checklist Criteria ---\n"
        for item in checklist:
            severity = item.get("severity", "info")
            label = item.get("label", "")
            desc = item.get("description", "")
            item_id = item.get("id", "")
            checklist_text += f"- [{severity.upper()}] {label} (id: {item_id}): {desc}\n"

    user_message = f"""Please analyze the following QC review feedback and suggest improvements to the template.

--- Current System Prompt ---
{template.system_prompt or '(No system prompt set)'}
{checklist_text}
{confirmed_text}
{dismissed_text}

Based on this review feedback, suggest changes to improve the template's system prompt and checklist criteria."""

    form_data = {
        "model": job.model_id,
        "messages": [
            {"role": "system", "content": SELF_IMPROVE_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "metadata": {
            "task": "qc_self_improve",
            "task_body": f"QC template self-improvement for job {job.id}",
        },
    }

    try:
        response = await generate_chat_completion(
            request,
            form_data,
            user=user,
            bypass_filter=True,
        )

        # Handle response
        if hasattr(response, "body"):
            body = b""
            async for chunk in response.body_iterator:
                if isinstance(chunk, bytes):
                    body += chunk
                else:
                    body += chunk.encode()
            response_data = json.loads(body)
        elif isinstance(response, dict):
            response_data = response
        else:
            response_data = json.loads(response)

        # Extract content
        content = ""
        if "choices" in response_data and response_data["choices"]:
            message = response_data["choices"][0].get("message", {})
            content = message.get("content", "")
        elif "message" in response_data:
            content = response_data["message"].get("content", "")

        return _parse_self_improve_response(content)

    except Exception as e:
        log.error(f"Error generating self-improve suggestions: {e}")
        return {
            "summary": f"Failed to generate suggestions: {str(e)}",
            "system_prompt_changes": [],
            "checklist_changes": [],
            "error": True,
        }


def _parse_self_improve_response(content: str) -> dict:
    """Parse the self-improve LLM response into structured suggestions."""
    content = content.strip()

    # Remove markdown code blocks if present
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines)

    try:
        result = json.loads(content)
        # Validate expected structure
        if "summary" not in result:
            result["summary"] = "Suggestions generated"
        if "system_prompt_changes" not in result:
            result["system_prompt_changes"] = []
        if "checklist_changes" not in result:
            result["checklist_changes"] = []
        return result
    except json.JSONDecodeError:
        return {
            "summary": "Could not parse AI response as structured suggestions.",
            "system_prompt_changes": [],
            "checklist_changes": [],
            "raw_response": content[:2000],
            "error": True,
        }


async def run_qc_job(
    request: Any,
    job_id: str,
    user: Any,
) -> dict:
    """
    Execute a full QC analysis job:
    1. Load job and documents
    2. For each document page, run AI analysis
    3. Create findings and annotated images
    4. Update job status
    """
    from io import BytesIO

    from open_webui.models.qc import (
        QCJobs,
        QCJobDocuments,
        QCFindings,
    )
    from open_webui.models.files import Files, FileForm
    from open_webui.storage.provider import Storage

    job = QCJobs.get_job_by_id(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    # Update status to running
    QCJobs.update_job_status(job_id, "running")

    # Clear previous findings from any prior run
    deleted = QCFindings.delete_findings_by_job_id(job_id)
    if deleted:
        log.info(f"Cleared {deleted} existing findings for job {job_id}")

    model_id = job.model_id
    system_prompt = job.system_prompt or QC_SYSTEM_PROMPT

    # Build full prompt from job meta
    meta = job.meta or {}
    checklist = meta.get("checklist_snapshot", [])
    kb_context = meta.get("kb_context", "")
    full_prompt = build_qc_prompt(system_prompt, checklist, kb_context)

    documents = QCJobDocuments.get_documents_by_job_id(job_id)

    # Build a map of document_id -> original PDF path for text search
    doc_pdf_paths = {}
    for doc in documents:
        try:
            file_record = Files.get_file_by_id(doc.file_id)
            if file_record:
                file_meta = file_record.meta or {}
                content_type = file_meta.get("content_type", "")
                file_name = file_meta.get("name", file_record.filename)
                if (
                    content_type == "application/pdf"
                    or file_name.lower().endswith(".pdf")
                ):
                    doc_pdf_paths[doc.id] = Storage.get_file(file_record.path)
        except Exception as e:
            log.debug(f"Could not resolve PDF path for doc {doc.id}: {e}")

    total_pages = 0
    total_findings = 0
    all_failed = True
    any_failed = False

    try:
        for doc in documents:
            try:
                QCJobDocuments.update_document(doc.id, status="processing")

                doc_meta = doc.meta or {}
                page_images = doc_meta.get("page_images", {})

                if not page_images:
                    log.warning(f"No page images for document {doc.id}")
                    QCJobDocuments.update_document(doc.id, status="failed")
                    any_failed = True
                    continue

                doc_findings = []
                annotated_images = {}

                for page_str, clean_file_id in page_images.items():
                    page_num = int(page_str)
                    total_pages += 1

                    # Get the clean page image
                    file_record = Files.get_file_by_id(clean_file_id)
                    if not file_record:
                        log.warning(f"Clean page image file {clean_file_id} not found")
                        continue

                    # Read the image file
                    file_path = Storage.get_file(file_record.path)
                    with open(file_path, "rb") as f:
                        page_image_bytes = f.read()

                    page_image_b64 = image_to_base64(page_image_bytes)

                    # Run AI analysis
                    result = await analyze_page(
                        request,
                        model_id,
                        full_prompt,
                        page_image_b64,
                        page_num,
                        user,
                    )

                    # Get next finding number
                    finding_number = QCFindings.get_next_finding_number(job_id)

                    page_findings_data = []
                    pdf_path = doc_pdf_paths.get(doc.id)

                    for ai_finding in result.get("findings", []):
                        ref_text = ai_finding.get("reference_text")
                        ai_location = ai_finding.get("location")
                        location_source = "ai"
                        locations_to_create = []

                        # Try text search refinement
                        if ref_text and pdf_path:
                            text_matches = find_text_on_page(
                                pdf_path, page_num, ref_text
                            )
                            if text_matches:
                                location_source = "text_search"
                                locations_to_create = text_matches
                            else:
                                locations_to_create = (
                                    [ai_location] if ai_location else [None]
                                )
                        else:
                            locations_to_create = (
                                [ai_location] if ai_location else [None]
                            )

                        for loc in locations_to_create:
                            finding_data = {
                                "id": str(uuid.uuid4()),
                                "job_id": job_id,
                                "document_id": doc.id,
                                "user_id": user.id,
                                "source": "ai",
                                "finding_number": finding_number,
                                "page_number": page_num,
                                "checklist_item_id": ai_finding.get(
                                    "checklist_item_id"
                                ),
                                "severity": ai_finding.get("severity", "info"),
                                "status": "open",
                                "title": ai_finding.get(
                                    "title", "Untitled Finding"
                                ),
                                "description": ai_finding.get(
                                    "description", ""
                                ),
                                "location": loc,
                                "ai_response": {
                                    "reasoning": ai_finding.get(
                                        "reasoning", ""
                                    ),
                                    "page_summary": result.get(
                                        "page_summary", ""
                                    ),
                                    "page_result": result.get(
                                        "page_result", ""
                                    ),
                                },
                                "meta": {
                                    "reference_text": ref_text,
                                    "location_source": location_source,
                                },
                                "created_at": int(time.time()),
                                "updated_at": int(time.time()),
                            }
                            QCFindings.insert_finding_raw(finding_data)
                            page_findings_data.append(finding_data)
                            total_findings += 1

                        finding_number += 1

                    doc_findings.extend(page_findings_data)

                    # Render annotated page image
                    if page_findings_data:
                        annotated_bytes = render_annotated_page(
                            page_image_bytes, page_findings_data
                        )
                    else:
                        annotated_bytes = page_image_bytes

                    # Save annotated image as a file
                    annotated_file_id = str(uuid.uuid4())
                    annotated_filename = f"{annotated_file_id}_qc_annotated_p{page_num}.png"
                    _, annotated_path = Storage.upload_file(
                        BytesIO(annotated_bytes),
                        annotated_filename,
                        {
                            "OpenWebUI-User-Id": user.id,
                            "OpenWebUI-File-Id": annotated_file_id,
                        },
                    )
                    Files.insert_new_file(
                        user.id,
                        FileForm(
                            **{
                                "id": annotated_file_id,
                                "filename": annotated_filename,
                                "path": annotated_path,
                                "meta": {
                                    "name": annotated_filename,
                                    "content_type": "image/png",
                                    "size": len(annotated_bytes),
                                    "qc_job_id": job_id,
                                    "qc_document_id": doc.id,
                                    "page_number": page_num,
                                    "annotated": True,
                                },
                            }
                        ),
                    )
                    annotated_images[str(page_num)] = annotated_file_id

                # Update document meta with annotated images
                updated_meta = {**(doc.meta or {}), "annotated_images": annotated_images}
                QCJobDocuments.update_document(
                    doc.id, status="completed", meta=updated_meta
                )
                all_failed = False

            except Exception as e:
                log.error(f"Error processing document {doc.id}: {e}")
                QCJobDocuments.update_document(doc.id, status="failed")
                any_failed = True

        # Determine overall result
        findings = QCFindings.get_findings_by_job_id(job_id)
        has_critical = any(f.severity == "critical" for f in findings)
        has_major = any(f.severity == "major" for f in findings)

        if all_failed:
            overall_result = None
            status = "failed"
        elif has_critical or has_major:
            overall_result = "fail"
            status = "completed"
        elif findings:
            overall_result = "flagged"
            status = "completed"
        else:
            overall_result = "pass"
            status = "completed"

        job_meta = {
            **(job.meta or {}),
            "statistics": {
                "pages_analyzed": total_pages,
                "findings_count": total_findings,
                "critical_count": sum(1 for f in findings if f.severity == "critical"),
                "major_count": sum(1 for f in findings if f.severity == "major"),
                "minor_count": sum(1 for f in findings if f.severity == "minor"),
                "info_count": sum(1 for f in findings if f.severity == "info"),
            },
        }

        updated_job = QCJobs.update_job_status(
            job_id, status, overall_result=overall_result, meta=job_meta
        )
        return updated_job.model_dump() if updated_job else {}

    except Exception as e:
        log.error(f"Error running QC job {job_id}: {e}")
        QCJobs.update_job_status(job_id, "failed")
        raise
