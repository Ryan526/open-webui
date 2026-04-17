"""Suppression rule evaluation + cluster key utilities."""

import hashlib
import logging
import re
from typing import Optional

from open_webui.models.qc import QCSuppressionRuleModel

log = logging.getLogger(__name__)


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    return re.sub(r"\s+", " ", title.strip().lower())


def _match(rule: QCSuppressionRuleModel, title: str, checklist_item_id: Optional[str]) -> bool:
    mt = (rule.match_type or "").strip()
    mv = rule.match_value or ""
    if not mv:
        return False
    tn = _normalize_title(title)
    mvn = _normalize_title(mv)

    if mt == "title_exact":
        return tn == mvn
    if mt == "title_contains":
        return mvn in tn if mvn else False
    if mt == "title_regex":
        try:
            return bool(re.search(mv, title or "", flags=re.IGNORECASE))
        except re.error as e:
            log.warning(f"Invalid regex in suppression rule {rule.id}: {e}")
            return False
    if mt == "checklist_item":
        return bool(checklist_item_id) and checklist_item_id == mv
    return False


def _scope_rank(rule: QCSuppressionRuleModel) -> int:
    """Lower rank = more specific. Used to order rule evaluation."""
    if rule.scope == "template":
        return 0
    if rule.scope == "project":
        return 1
    return 2  # global / other


def _severity_cap_blocks(rule: QCSuppressionRuleModel, severity: Optional[str]) -> bool:
    """If severity_filter is set, rule only applies when severity is at-or-below cap.

    Ordering: critical > major > minor > info.
    A rule with severity_filter='minor' suppresses only minor/info findings.
    """
    cap = (rule.severity_filter or "").strip().lower() or None
    if not cap:
        return False  # no cap -> never blocks
    order = ["info", "minor", "major", "critical"]
    try:
        cap_idx = order.index(cap)
    except ValueError:
        return False
    sev = (severity or "info").strip().lower()
    try:
        sev_idx = order.index(sev)
    except ValueError:
        sev_idx = 0
    # Only suppress if this finding's severity is <= cap
    return sev_idx > cap_idx


def _page_tag_blocks(rule: QCSuppressionRuleModel, page_type: Optional[str]) -> bool:
    pt = (rule.page_tag_filter or "").strip()
    if not pt:
        return False
    return (page_type or "").strip().lower() != pt.lower()


def evaluate_ai_finding(
    ai_finding: dict,
    rules: list[QCSuppressionRuleModel],
    *,
    page_type: Optional[str] = None,
    checklist_item_id: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """Return (should_suppress, matched_rule_id).

    Rules are evaluated most-specific-first (template → project → global).
    Cross-reference rules (page_type is None and checklist_item_id is None) only
    support title_* match types; checklist_item rules are skipped in that case.
    """
    if not rules:
        return (False, None)

    title = ai_finding.get("title") or ""
    severity = ai_finding.get("severity") or "info"
    is_xref_like = page_type is None and not checklist_item_id

    sorted_rules = sorted(rules, key=_scope_rank)
    for rule in sorted_rules:
        if not rule.enabled:
            continue
        if is_xref_like and rule.match_type == "checklist_item":
            continue
        if _severity_cap_blocks(rule, severity):
            continue
        if _page_tag_blocks(rule, page_type):
            continue
        if _match(rule, title, checklist_item_id):
            return (True, rule.id)
    return (False, None)


def compute_dup_cluster_key(
    title: str,
    document_id: Optional[str],
    page_number: Optional[int],
    location: Optional[dict],
) -> str:
    """Deterministic cluster key: normalized title + doc + page + bucketed location."""
    tn = _normalize_title(title)
    bucket = ""
    if isinstance(location, dict):
        try:
            x = round(float(location.get("x", 0)) / 0.05) * 0.05
            y = round(float(location.get("y", 0)) / 0.05) * 0.05
            bucket = f"{x:.2f}_{y:.2f}"
        except (TypeError, ValueError):
            bucket = ""
    raw = f"{tn}|{document_id or ''}|{page_number or 0}|{bucket}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
