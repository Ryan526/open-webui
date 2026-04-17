"""Test-run metric computation for QC test harness."""

import logging
import re
from difflib import SequenceMatcher
from typing import Optional

log = logging.getLogger(__name__)


TITLE_SIM_THRESHOLD = 0.6
LOCATION_IOU_THRESHOLD = 0.3
SEVERITIES = ("critical", "major", "minor", "info")


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    return re.sub(r"\s+", " ", title.strip().lower())


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


def _title_sim(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_title(a), _normalize_title(b)).ratio()


def _matches(produced: dict, expected: dict) -> bool:
    """Pairs a produced finding with an expected finding if same file+page + title sim
    (>= 0.6) and, when both have locations, IoU (>= 0.3). Match_title_patterns override
    the title similarity check when any pattern matches (regex).
    """
    # Must share page
    if (produced.get("page_number") or 0) != (expected.get("page_number") or 0):
        return False

    # Regex override on title
    patterns = expected.get("match_title_patterns") or []
    p_title = produced.get("title") or ""
    pattern_hit = False
    for p in patterns:
        if not p:
            continue
        try:
            if re.search(p, p_title, flags=re.IGNORECASE):
                pattern_hit = True
                break
        except re.error:
            continue

    if not pattern_hit:
        sim = _title_sim(p_title, expected.get("title") or "")
        if sim < TITLE_SIM_THRESHOLD:
            return False

    p_loc = produced.get("location") if isinstance(produced.get("location"), dict) else None
    e_loc = expected.get("location") if isinstance(expected.get("location"), dict) else None
    if p_loc is None and e_loc is None:
        return True
    if p_loc is None or e_loc is None:
        # One side has a location, the other doesn't — accept as match on title alone
        return True
    return _iou(p_loc, e_loc) >= LOCATION_IOU_THRESHOLD


def _file_id_of_produced(produced: dict, doc_file_id_by_job_doc_id: dict) -> Optional[str]:
    """Resolve a produced finding's `document_id` (qc_job_document.id) to its `file_id`."""
    doc_id = produced.get("document_id")
    if not doc_id:
        return None
    return doc_file_id_by_job_doc_id.get(doc_id)


def _file_id_of_expected(expected: dict, doc_file_id_by_testset_doc_id: dict) -> Optional[str]:
    doc_id = expected.get("document_id")
    if not doc_id:
        return None
    return doc_file_id_by_testset_doc_id.get(doc_id)


def compute_test_metrics(
    produced: list[dict],
    expected: list[dict],
    *,
    produced_doc_file_ids: Optional[dict] = None,
    expected_doc_file_ids: Optional[dict] = None,
) -> dict:
    """Greedy match produced vs expected findings and return metrics.

    Args:
      produced: list of produced (QCFinding-like) dicts.
      expected: list of expected (QCTestSetExpectedFinding-like) dicts.
      produced_doc_file_ids: map from QCJobDocument.id -> file_id, to align on file.
      expected_doc_file_ids: map from QCTestSetDocument.id -> file_id.

    Returns: {tp, fp, fn, precision, recall, f1, per_severity, unmatched_expected,
              unmatched_produced}
    """
    produced_doc_file_ids = produced_doc_file_ids or {}
    expected_doc_file_ids = expected_doc_file_ids or {}

    produced_remaining = list(produced)
    matched_pairs: list[tuple[dict, dict]] = []
    unmatched_expected: list[dict] = []

    for e in expected:
        e_file_id = _file_id_of_expected(e, expected_doc_file_ids)
        best_idx: Optional[int] = None
        best_score = -1.0
        for idx, p in enumerate(produced_remaining):
            p_file_id = _file_id_of_produced(p, produced_doc_file_ids)
            # Require same file when both are known
            if e_file_id and p_file_id and p_file_id != e_file_id:
                continue
            if not _matches(p, e):
                continue
            # Scoring: prefer higher title similarity
            sim = _title_sim(p.get("title") or "", e.get("title") or "")
            if sim > best_score:
                best_score = sim
                best_idx = idx
        if best_idx is not None:
            matched_pairs.append((produced_remaining.pop(best_idx), e))
        else:
            unmatched_expected.append(e)

    unmatched_produced = produced_remaining

    tp = len(matched_pairs)
    fp = len(unmatched_produced)
    fn = len(unmatched_expected)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    per_severity: dict[str, dict] = {s: {"tp": 0, "fp": 0, "fn": 0} for s in SEVERITIES}
    for p, _e in matched_pairs:
        sev = (p.get("severity") or "info").lower()
        if sev in per_severity:
            per_severity[sev]["tp"] += 1
    for p in unmatched_produced:
        sev = (p.get("severity") or "info").lower()
        if sev in per_severity:
            per_severity[sev]["fp"] += 1
    for e in unmatched_expected:
        sev = (e.get("severity") or "info").lower()
        if sev in per_severity:
            per_severity[sev]["fn"] += 1

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "per_severity": per_severity,
        "unmatched_expected": [e.get("id") for e in unmatched_expected],
        "unmatched_produced": [p.get("id") for p in unmatched_produced],
    }
