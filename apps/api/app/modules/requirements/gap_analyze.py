"""Deterministic NFR / requirements gap analysis for S1 interview."""

from __future__ import annotations

from app.modules.requirements.answer_checks import answer_satisfies
from app.modules.requirements.gap_models import Completeness, Gap, GapAnalysis, IntakeSnapshot
from app.modules.requirements.scorecard import (
    CODE_ORDER,
    code_label,
    is_ready,
    overall_score,
    score_categories,
    unlock_checks,
)

__all__ = ["CODE_ORDER", "analyze_gaps", "stub_prompt"]

# Interview kind bucket for each structural code (not the scorecard category).
_INTERVIEW_CATEGORY: dict[str, str] = {
    "current_approach": "requirements",
    "functional_scope": "requirements",
    "user_roles": "requirements",
    "business_rules": "requirements",
    "exception_handling": "requirements",
    "success_metrics": "nfrs",
    "implementation_language": "requirements",
    "integrations": "requirements",
    "team_constraints": "requirements",
    "rto_rpo": "nfrs",
    "peak_traffic": "nfrs",
    "data_residency": "nfrs",
    "auth_model": "security",
    "consistency": "nfrs",
    "cloud": "requirements",
}


def stub_prompt(code: str, *, preferred_cloud: str = "") -> str:
    """Neutral fallback when AI has not rewritten the question yet."""
    if code == "cloud" and preferred_cloud.strip():
        return f"Clarify: {code_label(code)} (intake says {preferred_cloud.strip()})."
    return f"Clarify: {code_label(code)}."


def _blob(snap: IntakeSnapshot) -> str:
    parts = [
        snap.business_objective,
        snap.problem_statement,
        snap.preferred_cloud,
        snap.scale_availability,
        snap.tech_constraints,
        *snap.requirement_texts,
    ]
    return " ".join(p for p in parts if p).lower()


def _intake_evidence_texts(snap: IntakeSnapshot, code: str) -> list[str]:
    """Intake snippets eligible for a gap — scoped per code, never the full blob."""
    if code == "cloud":
        values = [snap.preferred_cloud]
    elif code == "peak_traffic":
        values = [snap.scale_availability, *snap.requirement_texts]
    elif code == "rto_rpo":
        values = [snap.scale_availability, *snap.requirement_texts]
    elif code == "auth_model":
        values = [snap.tech_constraints, *snap.requirement_texts]
    elif code == "consistency":
        values = [snap.tech_constraints, *snap.requirement_texts]
    elif code == "data_residency":
        values = [snap.preferred_cloud, snap.tech_constraints, *snap.requirement_texts]
    elif code == "implementation_language":
        values = [snap.tech_constraints, *snap.intake_requirement_texts]
    elif code == "success_metrics":
        values = [
            snap.scale_availability,
            snap.business_objective,
            *snap.intake_requirement_texts,
        ]
    elif code in {"user_roles", "business_rules", "exception_handling"}:
        values = [*snap.intake_requirement_texts]
    elif code in {"current_approach", "functional_scope", "integrations", "team_constraints"}:
        values = []
    else:
        values = [
            snap.business_objective,
            snap.problem_statement,
            snap.preferred_cloud,
            snap.scale_availability,
            snap.tech_constraints,
            *snap.requirement_texts,
        ]
    out: list[str] = []
    for value in values:
        text = (value or "").strip()
        if text:
            out.append(text)
    return out


def _gap_satisfied(code: str, snap: IntakeSnapshot, blob: str) -> bool:
    """Gap is closed only when discrete text passes answer_satisfies.

    Interview answers and intake fields share the same validator. For codes that
    need multiple signals (e.g. RTO + RPO), scoped intake snippets may be joined
    — never the full unscoped blob.
    """
    del blob  # retained in signature for call-site compatibility
    answer = snap.answered_answers.get(code)
    if answer is not None and answer_satisfies(code, answer):
        return True
    texts = _intake_evidence_texts(snap, code)
    if any(answer_satisfies(code, text) for text in texts):
        return True
    if code in {"rto_rpo"} and len(texts) > 1:
        return answer_satisfies(code, "\n".join(texts))
    return False


def analyze_gaps(snap: IntakeSnapshot) -> GapAnalysis:
    blob = _blob(snap)
    gaps: list[Gap] = []
    captured: list[str] = []
    satisfied: dict[str, bool] = {}

    for code in CODE_ORDER:
        category = _INTERVIEW_CATEGORY.get(code, "requirements")
        ok = _gap_satisfied(code, snap, blob)
        label = code_label(code)
        if code == "cloud" and snap.preferred_cloud.strip():
            label = f"Cloud = {snap.preferred_cloud.strip()}"
        satisfied[code] = ok
        if ok:
            captured.append(label)
        else:
            gaps.append(
                Gap(
                    code=code,
                    prompt=stub_prompt(code, preferred_cloud=snap.preferred_cloud),
                    category=category,
                )
            )

    categories = score_categories(satisfied)
    overall = overall_score(categories)
    by_key = {c.key: c.score for c in categories}

    return GapAnalysis(
        gaps=gaps,
        captured=captured,
        completeness=Completeness(
            overall=overall,
            scope=by_key["scope"],
            story_readiness=by_key["story_readiness"],
            reliability=by_key["reliability"],
            security_compliance=by_key["security_compliance"],
            delivery=by_key["delivery"],
            categories=categories,
            ready=is_ready(categories, overall),
            unlock=unlock_checks(categories, overall),
        ),
    )
