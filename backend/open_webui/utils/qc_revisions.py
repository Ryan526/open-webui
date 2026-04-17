"""Finding matcher and diff utilities for QC revision comparison."""

import logging
import re
import time
import uuid
from difflib import SequenceMatcher
from typing import Optional

from open_webui.models.qc import (
    QCFinding,
    QCFindingModel,
    QCFindings,
    QCJobs,
)
from open_webui.internal.db import get_db_context

log = logging.getLogger(__name__)


MATCH_THRESHOLD = 0.55
TITLE_WEIGHT = 0.65
LOCATION_WEIGHT = 0.35


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    return re.sub(r"\s+", " ", title.strip().lower())


def _token_set_ratio(a: str, b: str) -> float:
    """Return a token-set similarity ratio in [0, 1].

    Prefers rapidfuzz when available; falls back to difflib on token-set strings.
    """
    a_n = _normalize_title(a)
    b_n = _normalize_title(b)
    if not a_n or not b_n:
        return 0.0
    try:
        from rapidfuzz import fuzz  # type: ignore

        return float(fuzz.token_set_ratio(a_n, b_n)) / 100.0
    except Exception:
        # Fallback: difflib on sorted unique tokens
        a_tokens = " ".join(sorted(set(a_n.split())))
        b_tokens = " ".join(sorted(set(b_n.split())))
        return SequenceMatcher(None, a_tokens, b_tokens).ratio()


def _rect(loc) -> Optional[tuple[float, float, float, float]]:
    if not loc or not isinstance(loc, dict):
        return None
    try:
        x = float(loc.get("x", 0))
        y = float(loc.get("y", 0))
        w = float(loc.get("width", 0))
        h = float(loc.get("height", 0))
    except (TypeError, ValueError):
        return None
    if w <= 0 or h <= 0:
        return None
    return (x, y, x + w, y + h)


def _iou(loc_a, loc_b) -> float:
    ra = _rect(loc_a)
    rb = _rect(loc_b)
    if ra is None or rb is None:
        return 0.0
    ix0 = max(ra[0], rb[0])
    iy0 = max(ra[1], rb[1])
    ix1 = min(ra[2], rb[2])
    iy1 = min(ra[3], rb[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = (ra[2] - ra[0]) * (ra[3] - ra[1])
    area_b = (rb[2] - rb[0]) * (rb[3] - rb[1])
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


def _pair_score(prev: QCFindingModel, new: QCFindingModel) -> float:
    title_sim = _token_set_ratio(prev.title or "", new.title or "")
    prev_loc = prev.location if isinstance(prev.location, dict) else None
    new_loc = new.location if isinstance(new.location, dict) else None

    if prev_loc is None or new_loc is None:
        # Drop IoU contribution; title only
        return title_sim
    loc_sim = _iou(prev_loc, new_loc)
    return TITLE_WEIGHT * title_sim + LOCATION_WEIGHT * loc_sim


def _page_key(f: QCFindingModel) -> tuple:
    return (f.page_number, f.checklist_item_id or "")


def match_findings(
    prev_findings: list[QCFindingModel],
    new_findings: list[QCFindingModel],
    threshold: float = MATCH_THRESHOLD,
) -> list[tuple[Optional[str], Optional[str], float]]:
    """Greedy matcher grouped by page.

    Returns a list of (prev_finding_id, new_finding_id, score) tuples.
    Unmatched prev entries yield (prev_id, None, 0.0).
    Unmatched new entries yield (None, new_id, 0.0).
    """
    matches: list[tuple[Optional[str], Optional[str], float]] = []

    # Group by page number (fallback key: None)
    prev_by_page: dict = {}
    for f in prev_findings:
        prev_by_page.setdefault(f.page_number, []).append(f)
    new_by_page: dict = {}
    for f in new_findings:
        new_by_page.setdefault(f.page_number, []).append(f)

    all_pages = set(prev_by_page.keys()) | set(new_by_page.keys())
    for page in all_pages:
        prev_list = list(prev_by_page.get(page, []))
        new_list = list(new_by_page.get(page, []))

        # Compute all pairs
        pairs: list[tuple[float, QCFindingModel, QCFindingModel]] = []
        for p in prev_list:
            for n in new_list:
                score = _pair_score(p, n)
                if score >= threshold:
                    pairs.append((score, p, n))
        pairs.sort(key=lambda t: t[0], reverse=True)

        used_prev: set = set()
        used_new: set = set()
        for score, p, n in pairs:
            if p.id in used_prev or n.id in used_new:
                continue
            used_prev.add(p.id)
            used_new.add(n.id)
            matches.append((p.id, n.id, score))

        for p in prev_list:
            if p.id not in used_prev:
                matches.append((p.id, None, 0.0))
        for n in new_list:
            if n.id not in used_new:
                matches.append((None, n.id, 0.0))

    return matches


def compute_diff(prev_job_id: str, new_job_id: str) -> dict:
    """Compute the revision diff between two jobs.

    Returns:
        dict with:
          - carried_over: list of {prev_finding, new_finding, score}
          - resolved: list of {prev_finding}
          - new: list of {new_finding}
          - stats: counts
    """
    prev = QCFindings.get_findings_by_job_id(prev_job_id) or []
    new = QCFindings.get_findings_by_job_id(new_job_id) or []

    # Exclude prior resolved-ghost rows from prev (already denote resolved state)
    prev = [f for f in prev if f.revision_state != "resolved"]

    matches = match_findings(prev, new)
    prev_by_id = {f.id: f for f in prev}
    new_by_id = {f.id: f for f in new}

    carried_over: list[dict] = []
    resolved: list[dict] = []
    new_only: list[dict] = []
    for prev_id, new_id, score in matches:
        if prev_id and new_id:
            carried_over.append(
                {
                    "prev_finding": prev_by_id[prev_id].model_dump(),
                    "new_finding": new_by_id[new_id].model_dump(),
                    "score": score,
                }
            )
        elif prev_id and not new_id:
            resolved.append({"prev_finding": prev_by_id[prev_id].model_dump()})
        elif new_id and not prev_id:
            new_only.append({"new_finding": new_by_id[new_id].model_dump()})

    stats = {
        "carried_over_count": len(carried_over),
        "resolved_count": len(resolved),
        "new_count": len(new_only),
        "prev_total": len(prev),
        "new_total": len(new),
    }
    return {
        "carried_over": carried_over,
        "resolved": resolved,
        "new": new_only,
        "stats": stats,
    }


def apply_diff_to_new_job(
    prev_job_id: str,
    new_job_id: str,
    *,
    create_resolved_ghosts: bool = False,
) -> dict:
    """Persist diff results onto the new job's findings.

    - Sets previous_finding_id + revision_state='carried_over' on matched new findings.
    - Sets revision_state='new' on unmatched new findings.
    - Optionally creates ghost rows with revision_state='resolved' referencing prev.

    Idempotent; re-applying yields the same state and records the apply timestamp.

    Returns dict with counts + marker timestamp.
    """
    diff = compute_diff(prev_job_id, new_job_id)

    carried_applied = 0
    resolved_created = 0
    new_tagged = 0

    new_job = QCJobs.get_job_by_id(new_job_id)
    if not new_job:
        return {"error": "new_job_not_found"}

    with get_db_context(None) as db:
        # Carried over: link prev -> new + inherit prev status for confirmed/dismissed
        for entry in diff["carried_over"]:
            prev_f = entry["prev_finding"]
            new_f = entry["new_finding"]

            new_row = db.query(QCFinding).filter_by(id=new_f["id"]).first()
            if not new_row:
                continue
            new_row.previous_finding_id = prev_f["id"]
            new_row.revision_state = "carried_over"
            # Inherit prev's reviewed status if current row is still default 'open'
            if new_row.status == "open" and prev_f.get("status") in (
                "confirmed",
                "dismissed",
            ):
                new_row.status = prev_f["status"]
            new_row.updated_at = int(time.time())
            carried_applied += 1

        # New: tag
        for entry in diff["new"]:
            new_f = entry["new_finding"]
            new_row = db.query(QCFinding).filter_by(id=new_f["id"]).first()
            if not new_row:
                continue
            new_row.revision_state = "new"
            new_row.updated_at = int(time.time())
            new_tagged += 1

        # Resolved ghosts
        if create_resolved_ghosts:
            for entry in diff["resolved"]:
                prev_f = entry["prev_finding"]
                # Skip if an idempotent ghost already exists (linked to this prev)
                existing = (
                    db.query(QCFinding)
                    .filter_by(
                        job_id=new_job_id,
                        previous_finding_id=prev_f["id"],
                        revision_state="resolved",
                    )
                    .first()
                )
                if existing:
                    continue
                # Next finding_number
                max_num_row = (
                    db.query(QCFinding.finding_number)
                    .filter_by(job_id=new_job_id)
                    .order_by(QCFinding.finding_number.desc())
                    .first()
                )
                next_num = (
                    (max_num_row[0] or 0) + 1
                    if max_num_row and max_num_row[0]
                    else 1
                )
                ghost = QCFinding(
                    id=str(uuid.uuid4()),
                    job_id=new_job_id,
                    document_id=prev_f.get("document_id"),
                    user_id=new_job.user_id,
                    source="cross_reference",
                    finding_number=next_num,
                    page_number=prev_f.get("page_number"),
                    checklist_item_id=prev_f.get("checklist_item_id"),
                    severity=prev_f.get("severity", "info"),
                    status="resolved",
                    title=prev_f.get("title", ""),
                    description=prev_f.get("description"),
                    location=prev_f.get("location"),
                    ai_response=None,
                    previous_finding_id=prev_f["id"],
                    revision_state="resolved",
                    meta={"revision_ghost": True},
                    created_at=int(time.time()),
                    updated_at=int(time.time()),
                )
                db.add(ghost)
                resolved_created += 1

        db.commit()

    # Record marker in job meta
    marker = int(time.time())
    job_meta = dict(new_job.meta or {})
    job_meta["revision_diff_applied_at"] = marker
    job_meta["revision_diff_stats"] = diff["stats"]
    with get_db_context(None) as db:
        from open_webui.models.qc import QCJob

        row = db.query(QCJob).filter_by(id=new_job_id).first()
        if row:
            row.meta = job_meta
            row.updated_at = int(time.time())
            db.commit()

    return {
        "carried_over_applied": carried_applied,
        "resolved_ghosts_created": resolved_created,
        "new_tagged": new_tagged,
        "applied_at": marker,
        "stats": diff["stats"],
    }
