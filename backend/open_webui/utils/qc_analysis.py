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
    extract_page_text,
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

IMPORTANT: Only create findings for actual problems, errors, or concerns that may need attention.
Do NOT create findings for items that appear correct or compliant — do not annotate something just to confirm it looks good.
If a checklist item passes with no issues, simply omit it from the findings. A finding must always represent a problem or potential problem.

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


####################
# Cross-Reference Analysis
####################

EXTRACTION_SYSTEM_PROMPT = """You are a data extraction assistant for electrical design documents. Extract structured information from the provided document page.

Return your response as a JSON object with this exact structure:
{
  "page_type": "panel_schedule|one_line|three_line|plan|detail|schedule|elevation|notes|cover|title_block|other",
  "sheet_id": "E-401 or null if not identifiable",
  "equipment_tags": [
    {"tag": "LP-2A", "type": "panel|transformer|disconnect|mcc|switchboard|motor|vfd|other", "attributes": {"bus": "225A", "main": "200A", "voltage": "480/277V"}}
  ],
  "circuit_references": [
    {"circuit": "20A/1P", "panel": "LP-2A", "description": "Lighting Circuit 2", "wire_size": "#12 AWG", "conduit": "3/4\\" EMT"}
  ],
  "wire_sizes": [
    {"size": "#12 AWG", "circuit_or_feeder": "LP-2A-2", "context": "branch circuit to lighting"}
  ],
  "cross_references": [
    {"text": "SEE DETAIL A ON E-501", "target_sheet": "E-501", "detail_or_note": "A"}
  ],
  "equipment_ratings": [
    {"tag": "TX-1", "rating": "75 kVA", "voltage_primary": "480V", "voltage_secondary": "208/120V", "impedance": "5.75%"}
  ],
  "conduit_schedule": [
    {"conduit_id": "C-1", "size": "3/4\\" EMT", "from": "Panel LP-2A", "to": "Junction Box JB-1"}
  ],
  "notes": ["Note 1: All conductors to be copper.", "Note 2: ..."]
}

Rules:
- Extract ALL equipment tags, circuit references, wire sizes, and cross-references visible on the page.
- Copy text labels EXACTLY as they appear (case-sensitive, include hyphens/spaces).
- For attributes, extract whatever is shown (ratings, sizes, voltages, etc.). Use null for unknown values.
- If a field has no data on this page, return an empty array.
- Return ONLY valid JSON, no markdown code blocks or other text."""


async def extract_page_structured_data(
    request: Any,
    model_id: str,
    pdf_path: Optional[str],
    page_number: int,
    page_image_b64: Optional[str],
    user: Any,
) -> dict:
    """
    Extract structured data from a single page.

    Uses PyMuPDF text extraction first. If substantial text is found (>200 chars),
    uses a text-only LLM call. Otherwise sends the page image for vision extraction.
    """
    from open_webui.utils.chat import generate_chat_completion

    # Try PyMuPDF text extraction first
    pymupdf_text = ""
    pymupdf_tables = []
    if pdf_path:
        page_data = extract_page_text(pdf_path, page_number)
        pymupdf_text = page_data.get("raw_text", "")
        pymupdf_tables = page_data.get("tables", [])

    # Build the user message content based on available data
    has_substantial_text = len(pymupdf_text.strip()) > 200

    if has_substantial_text:
        # Text-only extraction (cheaper — no image needed)
        table_text = ""
        if pymupdf_tables:
            table_text = "\n\n--- Tables Found on Page ---\n"
            for i, table in enumerate(pymupdf_tables, 1):
                table_text += f"\nTable {i}:\n"
                for row in table:
                    table_text += "  | " + " | ".join(
                        str(cell) if cell else "" for cell in row
                    ) + " |\n"

        user_content = (
            f"Extract structured data from page {page_number} of this electrical document.\n\n"
            f"--- Page Text ---\n{pymupdf_text}{table_text}"
        )
        messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
    elif page_image_b64:
        # Vision extraction (needed for graphical pages)
        context_hint = ""
        if pymupdf_text.strip():
            context_hint = f"\n\nText extracted from this page (may be partial):\n{pymupdf_text}"

        messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": page_image_b64}},
                    {
                        "type": "text",
                        "text": f"Extract structured data from page {page_number} of this electrical document.{context_hint}",
                    },
                ],
            },
        ]
    else:
        log.warning(f"No text or image available for page {page_number} extraction")
        return _empty_extraction()

    form_data = {
        "model": model_id,
        "messages": messages,
        "stream": False,
        "metadata": {
            "task": "qc_extraction",
            "task_body": f"Data extraction for page {page_number}",
        },
    }

    try:
        response = await generate_chat_completion(
            request, form_data, user=user, bypass_filter=True
        )

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

        content = ""
        if "choices" in response_data and response_data["choices"]:
            message = response_data["choices"][0].get("message", {})
            content = message.get("content", "")
        elif "message" in response_data:
            content = response_data["message"].get("content", "")

        return _parse_extraction_response(content)

    except Exception as e:
        log.error(f"Error extracting data from page {page_number}: {e}")
        return _empty_extraction()


def _empty_extraction() -> dict:
    """Return an empty extraction result."""
    return {
        "page_type": "other",
        "sheet_id": None,
        "equipment_tags": [],
        "circuit_references": [],
        "wire_sizes": [],
        "cross_references": [],
        "equipment_ratings": [],
        "conduit_schedule": [],
        "notes": [],
    }


def _parse_extraction_response(content: str) -> dict:
    """Parse the extraction LLM response into structured data."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines)

    try:
        result = json.loads(content)
        # Ensure all expected keys exist
        defaults = _empty_extraction()
        for key, default in defaults.items():
            if key not in result:
                result[key] = default
        return result
    except json.JSONDecodeError:
        log.warning("Failed to parse extraction response as JSON")
        return _empty_extraction()


def build_cross_reference_index(
    documents_data: list[dict],
) -> dict:
    """
    Aggregate extracted page data from all documents into a unified cross-reference index.

    Args:
        documents_data: List of dicts, each with:
          - document_id: str
          - document_name: str
          - pages: dict mapping page_number (int) -> extraction result dict

    Returns:
        Dict with aggregated data grouped by category for correlation analysis.
    """
    equipment_index = {}  # tag -> list of appearances
    circuit_index = {}    # circuit_key -> list of appearances
    wire_index = {}       # circuit/feeder -> list of wire size mentions
    xref_index = []       # all cross-sheet references
    rating_index = {}     # tag -> list of rating mentions
    sheet_ids = {}        # sheet_id -> {document_id, page_number}

    for doc in documents_data:
        doc_id = doc["document_id"]
        doc_name = doc.get("document_name", "Unknown")
        for page_num, page_data in doc["pages"].items():
            page_num = int(page_num)
            sheet_id = page_data.get("sheet_id")
            page_type = page_data.get("page_type", "other")

            if sheet_id:
                sheet_ids[sheet_id] = {
                    "document_id": doc_id,
                    "page_number": page_num,
                    "document_name": doc_name,
                }

            # Index equipment tags
            for equip in page_data.get("equipment_tags", []):
                tag = equip.get("tag", "").strip().upper()
                if not tag:
                    continue
                if tag not in equipment_index:
                    equipment_index[tag] = []
                equipment_index[tag].append({
                    "document_id": doc_id,
                    "document_name": doc_name,
                    "page_number": page_num,
                    "sheet_id": sheet_id,
                    "page_type": page_type,
                    "type": equip.get("type"),
                    "attributes": equip.get("attributes", {}),
                })

            # Index circuit references
            for circ in page_data.get("circuit_references", []):
                panel = (circ.get("panel") or "").strip().upper()
                circuit = (circ.get("circuit") or "").strip()
                key = f"{panel}:{circuit}" if panel else circuit
                if not key:
                    continue
                if key not in circuit_index:
                    circuit_index[key] = []
                circuit_index[key].append({
                    "document_id": doc_id,
                    "document_name": doc_name,
                    "page_number": page_num,
                    "sheet_id": sheet_id,
                    "page_type": page_type,
                    "description": circ.get("description"),
                    "wire_size": circ.get("wire_size"),
                    "conduit": circ.get("conduit"),
                })

            # Index wire sizes
            for wire in page_data.get("wire_sizes", []):
                feeder = (wire.get("circuit_or_feeder") or "").strip().upper()
                if not feeder:
                    continue
                if feeder not in wire_index:
                    wire_index[feeder] = []
                wire_index[feeder].append({
                    "document_id": doc_id,
                    "document_name": doc_name,
                    "page_number": page_num,
                    "sheet_id": sheet_id,
                    "page_type": page_type,
                    "size": wire.get("size"),
                    "context": wire.get("context"),
                })

            # Index cross-sheet references
            for xref in page_data.get("cross_references", []):
                target = xref.get("target_sheet")
                if target:
                    xref_index.append({
                        "source_document_id": doc_id,
                        "source_document_name": doc_name,
                        "source_page": page_num,
                        "source_sheet_id": sheet_id,
                        "text": xref.get("text", ""),
                        "target_sheet": target.strip().upper(),
                        "detail_or_note": xref.get("detail_or_note"),
                    })

            # Index equipment ratings
            for rating in page_data.get("equipment_ratings", []):
                tag = (rating.get("tag") or "").strip().upper()
                if not tag:
                    continue
                if tag not in rating_index:
                    rating_index[tag] = []
                rating_data = {k: v for k, v in rating.items() if k != "tag"}
                rating_data.update({
                    "document_id": doc_id,
                    "document_name": doc_name,
                    "page_number": page_num,
                    "sheet_id": sheet_id,
                    "page_type": page_type,
                })
                rating_index[tag].append(rating_data)

    return {
        "equipment": equipment_index,
        "circuits": circuit_index,
        "wires": wire_index,
        "cross_references": xref_index,
        "ratings": rating_index,
        "sheets": sheet_ids,
    }


CROSS_REFERENCE_SYSTEM_PROMPT = """You are an electrical design QC cross-reference analyst. You check consistency across all pages/sheets of an electrical drawing set.

You will receive structured data extracted from every page. Your job is to find INCONSISTENCIES and ERRORS across pages — things that don't match between sheets.

Check for these categories of issues:

1. **Equipment Tag Consistency**: Same equipment tag appears on multiple pages with different ratings, types, or attributes. (e.g., panel LP-2A shows 225A bus on the schedule but 200A bus on the one-line)

2. **Wire/Cable Size Mismatches**: Same circuit or feeder shows different wire sizes on different pages. (e.g., circuit LP-2A-4 shows #12 AWG on the panel schedule but #10 AWG on the plan)

3. **Cross-Sheet Reference Validity**: References like "See Detail A on E-501" — does sheet E-501 exist? (Check against the sheets index provided)

4. **Equipment Rating Consistency**: Same equipment tag shows different electrical ratings on different pages. (e.g., transformer TX-1 rated 75 kVA on the one-line but 50 kVA on the schedule)

5. **Circuit Completeness**: Circuits shown in a panel schedule should appear on plan pages. Flag circuits that only appear on one type of sheet.

Return your response as a JSON object:
{
  "cross_reference_findings": [
    {
      "title": "Brief description of the inconsistency",
      "description": "Detailed explanation of what doesn't match and where",
      "severity": "critical|major|minor|info",
      "cross_ref_type": "equipment_tag|wire_size|sheet_reference|equipment_rating|circuit_completeness",
      "references": [
        {"document_id": "...", "page_number": 3, "reference_text": "LP-2A", "context": "Panel schedule shows 225A bus"},
        {"document_id": "...", "page_number": 7, "reference_text": "LP-2A", "context": "One-line shows 200A bus"}
      ],
      "reasoning": "Why this inconsistency matters and potential impact"
    }
  ]
}

Guidelines:
- Only report REAL inconsistencies with specific evidence from the data.
- Do NOT flag items that appear on only one page unless they are broken cross-sheet references.
- Severity guide: critical = safety/code issue (wrong breaker/wire size), major = significant mismatch, minor = minor discrepancy, info = genuine ambiguity that warrants human review.
- Do NOT create findings for items that are consistent and correct — only report actual problems or genuine ambiguities.
- Include the exact document_id and page_number from the source data in references.
- If no cross-reference issues are found, return an empty findings array.
- Return ONLY valid JSON, no markdown code blocks or other text."""


def _build_correlation_chunks(index: dict, max_chars: int = 80000) -> list[dict]:
    """
    Split cross-reference index into themed chunks if the total data
    exceeds max_chars. Each chunk focuses on specific categories.

    Returns list of dicts with 'categories' (list of str) and 'text' (str).
    """
    sections = {}

    # Equipment tags section
    if index["equipment"]:
        lines = ["=== EQUIPMENT TAGS (appearances across all pages) ===\n"]
        for tag, appearances in sorted(index["equipment"].items()):
            if len(appearances) < 2:
                continue  # Only interesting if appears on multiple pages
            lines.append(f"\n{tag}:")
            for app in appearances:
                attrs = app.get("attributes", {})
                attr_str = ", ".join(f"{k}={v}" for k, v in attrs.items() if v) if attrs else "no attributes"
                lines.append(
                    f"  Page {app['page_number']} ({app.get('sheet_id', '?')}, {app['page_type']}): "
                    f"type={app.get('type', '?')}, {attr_str} [doc:{app['document_id'][:8]}]"
                )
        sections["equipment_tags"] = "\n".join(lines)

    # Equipment ratings section
    if index["ratings"]:
        lines = ["=== EQUIPMENT RATINGS (across all pages) ===\n"]
        for tag, ratings in sorted(index["ratings"].items()):
            if len(ratings) < 2:
                continue
            lines.append(f"\n{tag}:")
            for r in ratings:
                rating_str = ", ".join(
                    f"{k}={v}" for k, v in r.items()
                    if k not in ("document_id", "document_name", "page_number", "sheet_id", "page_type") and v
                )
                lines.append(
                    f"  Page {r['page_number']} ({r.get('sheet_id', '?')}, {r['page_type']}): "
                    f"{rating_str} [doc:{r['document_id'][:8]}]"
                )
        sections["equipment_ratings"] = "\n".join(lines)

    # Wire sizes section
    if index["wires"]:
        lines = ["=== WIRE SIZES (by circuit/feeder across all pages) ===\n"]
        for feeder, wires in sorted(index["wires"].items()):
            if len(wires) < 2:
                continue
            lines.append(f"\n{feeder}:")
            for w in wires:
                lines.append(
                    f"  Page {w['page_number']} ({w.get('sheet_id', '?')}, {w['page_type']}): "
                    f"size={w.get('size', '?')}, context={w.get('context', '?')} [doc:{w['document_id'][:8]}]"
                )
        sections["wire_sizes"] = "\n".join(lines)

    # Cross-sheet references section
    if index["cross_references"]:
        lines = ["=== CROSS-SHEET REFERENCES ===\n"]
        lines.append(f"Known sheets in document set: {', '.join(sorted(index['sheets'].keys())) or 'none identified'}\n")
        for xref in index["cross_references"]:
            target = xref["target_sheet"]
            resolved = target in index["sheets"]
            lines.append(
                f"  Page {xref['source_page']} ({xref.get('source_sheet_id', '?')}): "
                f"\"{xref['text']}\" -> target {target} "
                f"{'[FOUND]' if resolved else '[NOT FOUND]'} [doc:{xref['source_document_id'][:8]}]"
            )
        sections["sheet_references"] = "\n".join(lines)

    # Circuit completeness section
    if index["circuits"]:
        lines = ["=== CIRCUIT REFERENCES (by panel:circuit across all pages) ===\n"]
        for key, circs in sorted(index["circuits"].items()):
            page_types = set(c.get("page_type", "?") for c in circs)
            if len(circs) < 2 and len(page_types) <= 1:
                continue
            lines.append(f"\n{key}: (appears on {len(circs)} pages, types: {', '.join(page_types)})")
            for c in circs:
                wire_str = f", wire={c['wire_size']}" if c.get("wire_size") else ""
                lines.append(
                    f"  Page {c['page_number']} ({c.get('sheet_id', '?')}, {c['page_type']}): "
                    f"{c.get('description', '?')}{wire_str} [doc:{c['document_id'][:8]}]"
                )
        sections["circuit_completeness"] = "\n".join(lines)

    # Check if everything fits in one chunk
    full_text = "\n\n".join(sections.values())
    if len(full_text) <= max_chars:
        return [{"categories": list(sections.keys()), "text": full_text}]

    # Split into themed chunks
    chunks = []
    for category, text in sections.items():
        if len(text) > max_chars:
            # Single section too large — truncate with notice
            text = text[:max_chars - 100] + "\n\n[TRUNCATED — data exceeds context limit]"
        chunks.append({"categories": [category], "text": text})

    return chunks


async def run_cross_reference_analysis(
    request: Any,
    model_id: str,
    index: dict,
    user: Any,
    custom_instructions: Optional[str] = None,
) -> list[dict]:
    """
    Run cross-reference correlation analysis on the aggregated index.

    Returns a list of cross-reference finding dicts ready for insertion.
    """
    from open_webui.utils.chat import generate_chat_completion

    chunks = _build_correlation_chunks(index)

    if not chunks or all(not c["text"].strip() for c in chunks):
        log.info("No cross-reference data to analyze (no multi-page items found)")
        return []

    all_findings = []

    for chunk in chunks:
        prompt = CROSS_REFERENCE_SYSTEM_PROMPT
        if custom_instructions:
            prompt += f"\n\n--- Additional Instructions ---\n{custom_instructions}"

        user_message = (
            f"Analyze the following cross-reference data for inconsistencies.\n"
            f"Categories in this batch: {', '.join(chunk['categories'])}\n\n"
            f"{chunk['text']}"
        )

        form_data = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
            "metadata": {
                "task": "qc_cross_reference",
                "task_body": f"Cross-reference analysis: {', '.join(chunk['categories'])}",
            },
        }

        try:
            response = await generate_chat_completion(
                request, form_data, user=user, bypass_filter=True
            )

            if hasattr(response, "body"):
                body = b""
                async for chunk_data in response.body_iterator:
                    if isinstance(chunk_data, bytes):
                        body += chunk_data
                    else:
                        body += chunk_data.encode()
                response_data = json.loads(body)
            elif isinstance(response, dict):
                response_data = response
            else:
                response_data = json.loads(response)

            content = ""
            if "choices" in response_data and response_data["choices"]:
                message = response_data["choices"][0].get("message", {})
                content = message.get("content", "")
            elif "message" in response_data:
                content = response_data["message"].get("content", "")

            parsed = _parse_cross_reference_response(content)
            all_findings.extend(parsed)

        except Exception as e:
            log.error(f"Error in cross-reference analysis for {chunk['categories']}: {e}")

    return all_findings


def _parse_cross_reference_response(content: str) -> list[dict]:
    """Parse the cross-reference LLM response into a list of finding dicts."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines)

    try:
        result = json.loads(content)
        findings = result.get("cross_reference_findings", [])
        # Validate structure
        validated = []
        for f in findings:
            if not f.get("title"):
                continue
            validated.append({
                "title": f.get("title", ""),
                "description": f.get("description", ""),
                "severity": f.get("severity", "major"),
                "cross_ref_type": f.get("cross_ref_type", ""),
                "references": f.get("references", []),
                "reasoning": f.get("reasoning", ""),
            })
        return validated
    except json.JSONDecodeError:
        log.warning("Failed to parse cross-reference response as JSON")
        return []


SELF_IMPROVE_SYSTEM_PROMPT = """You are a QC template optimization assistant. You analyze feedback from QC reviews to suggest improvements to QC templates.

You will receive:
1. The current template system prompt
2. The current checklist criteria
3. Confirmed findings — real issues the AI correctly identified
4. Dismissed findings with reasons — false positives that should be avoided
5. Missed issues — real issues a human reviewer found that the AI failed to detect

Your task is to suggest changes to the system prompt and checklist that would:
- Reduce false positives (based on dismissed findings and their reasons)
- Reinforce patterns that correctly identified real issues
- Add new checklist items if review feedback suggests gaps
- Add detection patterns for issues the AI missed (based on missed issues with their descriptions)

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
    # Human findings are always included regardless of status —
    # every manual annotation represents something the AI should have caught
    missed = [f for f in findings if f.source == "human"]

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

    missed_text = ""
    if missed:
        missed_text = "\n--- Missed Issues (Human-Added, AI Failed to Detect) ---\n"
        for f in missed:
            missed_text += f"- [{f.severity.upper()}] {f.title}: {f.description or 'No description'}\n"
            if f.page_number:
                missed_text += f"  Page: {f.page_number}\n"

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
{missed_text}

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

        # ─── Pass 2: Cross-Reference Analysis ───
        cross_ref_config = meta.get("cross_reference_analysis", {})
        cross_ref_enabled = cross_ref_config.get("enabled", False)
        cross_ref_findings_count = 0

        if cross_ref_enabled and not all_failed:
            log.info(f"Starting cross-reference analysis for job {job_id}")

            # Update progress
            progress_meta = {**(job.meta or {}), "progress": {
                "phase": "cross_reference_extraction",
                "detail": "Extracting structured data from pages...",
            }}
            QCJobs.update_job_status(job_id, "running", meta=progress_meta)

            # Step A: Extract structured data from each page
            documents_data = []
            for doc in documents:
                doc_meta = doc.meta or {}
                page_images = doc_meta.get("page_images", {})
                if not page_images:
                    continue

                pdf_path = doc_pdf_paths.get(doc.id)
                page_extractions = {}

                for page_str, clean_file_id in page_images.items():
                    page_num = int(page_str)

                    # Get page image for vision extraction (if needed)
                    page_image_b64 = None
                    try:
                        file_record = Files.get_file_by_id(clean_file_id)
                        if file_record:
                            fp = Storage.get_file(file_record.path)
                            with open(fp, "rb") as f:
                                page_image_b64 = image_to_base64(f.read())
                    except Exception as e:
                        log.debug(f"Could not load page image for extraction: {e}")

                    try:
                        extracted = await extract_page_structured_data(
                            request, model_id, pdf_path, page_num,
                            page_image_b64, user,
                        )
                        page_extractions[str(page_num)] = extracted
                    except Exception as e:
                        log.warning(f"Extraction failed for doc {doc.id} page {page_num}: {e}")

                # Store extracted data in document meta
                if page_extractions:
                    updated_meta = {**(doc.meta or {}), "extracted_data": page_extractions}
                    QCJobDocuments.update_document(doc.id, meta=updated_meta)

                # Get document name for the index
                doc_name = "Unknown"
                try:
                    file_record = Files.get_file_by_id(doc.file_id)
                    if file_record:
                        doc_name = (file_record.meta or {}).get("name", file_record.filename)
                except Exception:
                    pass

                documents_data.append({
                    "document_id": doc.id,
                    "document_name": doc_name,
                    "pages": page_extractions,
                })

            # Step B: Build index and run correlation
            if documents_data:
                progress_meta = {**(job.meta or {}), "progress": {
                    "phase": "cross_reference_correlation",
                    "detail": f"Cross-referencing data across {total_pages} pages...",
                }}
                QCJobs.update_job_status(job_id, "running", meta=progress_meta)

                xref_index = build_cross_reference_index(documents_data)

                xref_findings = await run_cross_reference_analysis(
                    request, model_id, xref_index, user,
                    custom_instructions=system_prompt if system_prompt != QC_SYSTEM_PROMPT else None,
                )

                # Insert cross-reference findings
                for xref_finding in xref_findings:
                    refs = xref_finding.get("references", [])
                    # Use first reference as the primary location
                    primary_doc_id = refs[0]["document_id"] if refs else None
                    primary_page = refs[0]["page_number"] if refs else None
                    primary_ref_text = refs[0].get("reference_text") if refs else None

                    finding_number = QCFindings.get_next_finding_number(job_id)
                    finding_data = {
                        "id": str(uuid.uuid4()),
                        "job_id": job_id,
                        "document_id": primary_doc_id,
                        "user_id": user.id,
                        "source": "cross_reference",
                        "finding_number": finding_number,
                        "page_number": primary_page,
                        "checklist_item_id": None,
                        "severity": xref_finding.get("severity", "major"),
                        "status": "open",
                        "title": xref_finding.get("title", "Cross-Reference Issue"),
                        "description": xref_finding.get("description", ""),
                        "location": None,
                        "ai_response": {
                            "reasoning": xref_finding.get("reasoning", ""),
                        },
                        "meta": {
                            "source": "cross_reference",
                            "cross_ref_type": xref_finding.get("cross_ref_type", ""),
                            "references": refs,
                            "reference_text": primary_ref_text,
                            "location_source": "cross_reference",
                        },
                        "created_at": int(time.time()),
                        "updated_at": int(time.time()),
                    }
                    QCFindings.insert_finding_raw(finding_data)
                    total_findings += 1
                    cross_ref_findings_count += 1

                log.info(
                    f"Cross-reference analysis complete for job {job_id}: "
                    f"{cross_ref_findings_count} findings"
                )

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
            "progress": None,  # Clear progress indicator
            "statistics": {
                "pages_analyzed": total_pages,
                "findings_count": total_findings,
                "cross_ref_findings_count": cross_ref_findings_count,
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
