"""Duplicate clustering for QC findings within a single job."""

import logging
import re
from typing import Optional

from sqlalchemy import select

from open_webui.models.qc import QCFindings, QCFinding
from open_webui.internal.db import get_async_db_context

log = logging.getLogger(__name__)

TITLE_JACCARD_THRESHOLD = 0.9
LOCATION_IOU_THRESHOLD = 0.4

SEVERITY_ORDER = {"critical": 3, "major": 2, "minor": 1, "info": 0}


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    return re.sub(r"\s+", " ", title.strip().lower())


def _tokens(title: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (title or "").lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    if union == 0:
        return 0.0
    return inter / union


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


def _iou(a, b) -> float:
    ra = _rect(a)
    rb = _rect(b)
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


def _is_duplicate(a, b) -> bool:
    # Same page + same doc (group key). Check normalized-title equality OR Jaccard >= 0.9.
    at = _normalize_title(a.title or "")
    bt = _normalize_title(b.title or "")
    if not at or not bt:
        return False
    same_title = at == bt
    jaccard_ok = _jaccard(_tokens(at), _tokens(bt)) >= TITLE_JACCARD_THRESHOLD
    if not (same_title or jaccard_ok):
        return False

    la = a.location if isinstance(a.location, dict) else None
    lb = b.location if isinstance(b.location, dict) else None
    if la is None and lb is None:
        return True
    if la is None or lb is None:
        # One has a location, the other doesn't — accept as dup since titles match
        return True
    return _iou(la, lb) >= LOCATION_IOU_THRESHOLD


def _canonical_of(group: list) -> object:
    """Pick canonical: lowest finding_number; tie-break by highest severity."""
    def key(f):
        fn = f.finding_number if f.finding_number is not None else 10**9
        sev = -SEVERITY_ORDER.get((f.severity or "info").lower(), 0)
        return (fn, sev)

    return min(group, key=key)


async def find_and_link_duplicates(job_id: str) -> int:
    """Cluster near-duplicate findings within a job and set canonical_finding_id.

    Returns number of findings newly linked to a canonical (excluding the canonicals themselves).
    Does not delete any finding.
    """
    findings = await QCFindings.get_findings_by_job_id(job_id) or []
    # Only consider findings that aren't ghost-resolved and aren't already linked to canonical
    active = [
        f for f in findings
        if (f.revision_state != "resolved")
    ]

    # Group by (document_id, page_number)
    groups: dict = {}
    for f in active:
        key = (f.document_id or "", f.page_number or 0)
        groups.setdefault(key, []).append(f)

    linked_total = 0
    async with get_async_db_context(None) as db:
        for key, group in groups.items():
            if len(group) < 2:
                continue
            # Greedy cluster-forming
            remaining = list(group)
            while remaining:
                seed = remaining.pop(0)
                cluster = [seed]
                nxt: list = []
                for other in remaining:
                    if _is_duplicate(seed, other):
                        cluster.append(other)
                    else:
                        nxt.append(other)
                remaining = nxt
                if len(cluster) < 2:
                    continue
                canonical = _canonical_of(cluster)
                canonical_id = canonical.id
                for member in cluster:
                    new_val = None if member.id == canonical_id else canonical_id
                    # Skip write if already correct
                    row = (await db.execute(select(QCFinding).filter_by(id=member.id))).scalars().first()
                    if not row:
                        continue
                    if row.canonical_finding_id == new_val:
                        continue
                    row.canonical_finding_id = new_val
                    if new_val:
                        linked_total += 1
        await db.commit()

    return linked_total
