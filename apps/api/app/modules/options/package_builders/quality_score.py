"""Explainable architecture evidence checklist — coverage states, not a 0–100 score."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Literal

from app.modules.options.generator import OptionTemplate, ProjectContext
from app.modules.options.package_builders._shared import _context_blob

Coverage = Literal["missing", "partial", "evidenced", "verified"]

COVERAGE_STATES: tuple[Coverage, ...] = ("missing", "partial", "evidenced", "verified")

SCORE_WEIGHTS: dict[str, int] = {
    "requirements_completeness": 20,
    "scalability": 15,
    "reliability": 15,
    "security": 15,
    "operability": 10,
    "data_architecture": 10,
    "integration_design": 5,
    "maintainability": 5,
    "cost_awareness": 5,
    "governance_compliance": 5,
}

_NEGATION_PREFIX = re.compile(
    r"(?:\bno|not|without|lack(?:ing)?\s+of|don't|dont|doesn't|doesnt|no\s+)\s*$",
    re.IGNORECASE,
)


def _rank(state: Coverage) -> int:
    return COVERAGE_STATES.index(state)


def _weaker(a: Coverage, b: Coverage) -> Coverage:
    return a if _rank(a) <= _rank(b) else b


def _from_interview_score(n: int) -> Coverage:
    """Map interview category / overall completeness onto a coverage ceiling."""
    if n < 40:
        return "missing"
    if n < 70:
        return "partial"
    if n < 85:
        return "evidenced"
    return "verified"


def _apply_interview_cap(state: Coverage, interview_score: int | None) -> Coverage:
    """Keyword presence alone never reaches verified; interview must confirm.

    When an interview floor is provided, the result cannot exceed that floor.
    When interview confirms (>=85) and keywords already reached evidenced, promote
    to verified.
    """
    if interview_score is None:
        return "evidenced" if state == "verified" else state
    floor = _from_interview_score(interview_score)
    capped = _weaker(state, floor)
    if interview_score >= 85 and state == "evidenced":
        return "verified"
    return capped


def _keyword_present(blob: str, keyword: str) -> bool:
    """True when ``keyword`` appears and is not negated in the preceding window."""
    needle = keyword.lower()
    hay = blob.lower()
    start = 0
    while True:
        idx = hay.find(needle, start)
        if idx < 0:
            return False
        window = hay[max(0, idx - 28) : idx]
        if not _NEGATION_PREFIX.search(window.rstrip()):
            return True
        start = idx + len(needle)


def _any_keyword(blob: str, keywords: tuple[str, ...]) -> bool:
    return any(_keyword_present(blob, k) for k in keywords)


def _has_duration_near(blob: str, keyword: str) -> bool:
    """Require a digit/time unit near the keyword so bare 'rto' does not score."""
    hay = blob.lower()
    needle = keyword.lower()
    start = 0
    while True:
        idx = hay.find(needle, start)
        if idx < 0:
            return False
        window = hay[max(0, idx - 28) : idx]
        if _NEGATION_PREFIX.search(window.rstrip()):
            start = idx + len(needle)
            continue
        vicinity = hay[idx : idx + len(needle) + 24]
        if re.search(r"\d", vicinity) and re.search(
            r"(?:ms|s|sec|secs|second|minute|min|mins|hour|hr|hrs|day|days|m\b|h\b)",
            vicinity,
        ):
            return True
        start = idx + len(needle)


def build_quality_score(
    ctx: ProjectContext,
    option: OptionTemplate,
    *,
    completeness_overall: int,
    evidence_citation_count: int,
    org_standards_cited: bool = False,
    completeness_categories: Mapping[str, int] | None = None,
) -> dict:
    """Evidence checklist — coverage states for what intake/interview captured.

    States: ``missing`` → ``partial`` → ``evidenced`` → ``verified``.
    Keyword scraping alone tops out at ``evidenced``; ``verified`` needs an
    interview floor (>=85) confirming the dimension (or requirements completeness).

    ``option`` is used only for alignment notes/deductions, never free coverage
    from cost_band / ops_band.
    """
    missing: list[str] = []
    blockers: list[str] = []
    alignment: list[str] = []
    blob = _context_blob(ctx)

    req_n = max(0, min(100, completeness_overall))
    req: Coverage = _from_interview_score(req_n)
    if req_n < 70:
        missing.append("Interview completeness below 70%")
    if req_n < 40:
        blockers.append("Requirements too incomplete to trust the package")

    # Scalability — quantified load/scale evidence only
    scale_field = (ctx.scale_availability or "").lower()
    has_scale_metric = _any_keyword(
        scale_field or blob,
        ("peak", "tps", "events/sec", "throughput", "/sec", "qps", "rps"),
    ) and any(ch.isdigit() for ch in (ctx.scale_availability or blob))
    if has_scale_metric and any(ch.isdigit() for ch in (ctx.scale_availability or "")):
        scale: Coverage = "evidenced"
    elif has_scale_metric:
        scale = "partial"
    else:
        scale = "missing"
        missing.append("No quantified scale / peak load in intake")

    # Reliability — RTO/RPO with a duration, or explicit HA (not negated)
    has_rto = _has_duration_near(blob, "rto")
    has_rpo = _has_duration_near(blob, "rpo")
    has_ha = _any_keyword(blob, ("multi-region", "failover", "disaster recovery"))
    if has_rto and has_rpo:
        reliability: Coverage = "evidenced"
    elif has_rto or has_rpo or has_ha:
        reliability = "partial"
    else:
        reliability = "missing"
        missing.append("Missing RTO/RPO or HA targets in interview/intake")

    # Security — concrete control names, negation-aware
    has_auth = _any_keyword(
        blob,
        ("oidc", "oauth", "authn", "authz", "mtls", "rbac", "sso", "jwt"),
    )
    if has_auth:
        security: Coverage = "evidenced"
    else:
        security = "missing"
        missing.append("Authn/z or security controls not evidenced")

    # Operability — interview evidence only (never option.ops_band)
    if _any_keyword(blob, ("on-call", "runbook", "slo", "observability", "golden signal")):
        operability: Coverage = "evidenced"
    else:
        operability = "missing"
        missing.append("No operability / observability evidence in interview")

    # Data architecture — only if a store is required by constraints/requirements
    has_data = _any_keyword(
        blob, ("postgres", "sql", "cosmos", "database", "system of record", "store")
    )
    data_arch: Coverage = "evidenced" if has_data else "missing"
    if not has_data:
        missing.append("No data-store requirements captured")

    # Integration — only if messaging/integration is evidenced in context
    has_integration = _any_keyword(
        blob, ("kafka", "event", "queue", "integration", "api gateway", "pubsub")
    )
    integration: Coverage = "evidenced" if has_integration else "missing"
    if not has_integration:
        missing.append("No integration / messaging requirements captured")

    # Maintainability — ownership / ADR review evidence from interview
    has_ownership = _any_keyword(
        blob, ("owner", "raci", "steward", "platform team", "adr review")
    )
    maintainability: Coverage = "evidenced" if has_ownership else "missing"
    if not has_ownership:
        missing.append("No ownership / review stewardship evidenced")

    # Cost — intake evidence only (never option.cost_band)
    if _any_keyword(blob, ("budget", "cost cap", "finops", "cost target", "$/month", "tco")):
        cost: Coverage = "evidenced"
    else:
        cost = "missing"
        missing.append("No cost / budget evidence in interview or intake")

    # Governance — org/project standards only (never seed)
    if org_standards_cited or evidence_citation_count >= 2:
        governance: Coverage = "evidenced"
    elif evidence_citation_count > 0:
        governance = "partial"
    else:
        governance = "missing"
        missing.append("No org or project standards cited")
    if org_standards_cited:
        governance = "verified"

    # Option alignment — deductions / notes only
    stack_l = {s.lower() for s in (option.stack or [])}
    if any(s in stack_l for s in ("kafka", "pubsub", "service-bus", "event-hubs")) and not has_integration:
        alignment.append("Option claims messaging stack without integration evidence in intake")
        integration = _weaker(integration, "partial")
    if any(s in stack_l for s in ("postgres", "sql", "cosmos", "redis")) and not has_data:
        alignment.append("Option claims a datastore without data-store evidence in intake")
        data_arch = _weaker(data_arch, "partial")
    missing.extend(alignment)

    caps = completeness_categories or {}
    reliability_cap = caps.get("reliability")
    before_rel = reliability
    reliability = _apply_interview_cap(reliability, reliability_cap)
    if reliability_cap is not None and _rank(reliability) < _rank(before_rel):
        missing.append("Reliability questions still open in the interview")

    security_cap = caps.get("security_compliance")
    before_sec = security
    security = _apply_interview_cap(security, security_cap)
    if security_cap is not None and _rank(security) < _rank(before_sec):
        missing.append("Security & compliance questions still open in the interview")

    # Dimensions without interview floors never claim verified
    scale = _apply_interview_cap(scale, None)
    operability = _apply_interview_cap(operability, None)
    data_arch = _apply_interview_cap(data_arch, None)
    integration = _apply_interview_cap(integration, None)
    maintainability = _apply_interview_cap(maintainability, None)
    cost = _apply_interview_cap(cost, None)
    if not org_standards_cited:
        governance = _apply_interview_cap(governance, None)

    raw: dict[str, Coverage] = {
        "requirements_completeness": req,
        "scalability": scale,
        "reliability": reliability,
        "security": security,
        "operability": operability,
        "data_architecture": data_arch,
        "integration_design": integration,
        "maintainability": maintainability,
        "cost_awareness": cost,
        "governance_compliance": governance,
    }
    categories = [
        {
            "id": key,
            "label": key.replace("_", " ").title(),
            "weight": weight,
            "coverage": raw[key],
        }
        for key, weight in SCORE_WEIGHTS.items()
    ]
    overall = min((c["coverage"] for c in categories), key=_rank)
    strong_hits = sum(
        1
        for v in (has_scale_metric, has_rto and has_rpo, has_auth, has_data, has_integration)
        if v
    )
    confidence = "medium" if strong_hits >= 3 and req_n >= 70 else "low"
    return {
        "overall": overall,
        "categories": categories,
        "missing_evidence": missing,
        "blockers": blockers,
        "label": "evidence_checklist",
        "method": "intake_keyword_presence",
        "confidence": confidence,
    }
