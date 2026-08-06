"""Interview assist: problem-specific requirement confirmation, not a generic NFR quiz."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from app.ai.assist_status import AiAssistStatus, as_ai_failure
from app.ai.gateway import AIGateway
from app.ai.schemas import ChatMessage

if TYPE_CHECKING:
    from app.modules.requirements.gaps import Gap, IntakeSnapshot


class InterviewAssistResult(BaseModel):
    intro: str | None = None
    rewrites: dict[str, str] = Field(default_factory=dict)
    followups: list[Any] = Field(default_factory=list)
    sufficient: bool = False
    status: AiAssistStatus = Field(default_factory=AiAssistStatus)


INTERVIEW_ASSIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intro": {"type": "string"},
        "rewrites": {
            "type": "object",
            "additionalProperties": {"type": "string"},
        },
        "sufficient": {"type": "boolean"},
        "followup": {
            "type": ["object", "null"],
            "properties": {
                "code": {"type": "string"},
                "prompt": {"type": "string"},
                "category": {"type": "string"},
            },
            "required": ["code", "prompt", "category"],
        },
    },
    "required": ["intro", "rewrites", "sufficient", "followup"],
}

ACK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"reply": {"type": "string"}},
    "required": ["reply"],
}

ANSWER_SUGGESTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"suggestion": {"type": "string"}},
    "required": ["suggestion"],
}


def _project_blurb(snap: IntakeSnapshot) -> str:
    return (
        f"Objective: {snap.business_objective or '—'}\n"
        f"Problem: {snap.problem_statement or '—'}\n"
        f"Cloud: {snap.preferred_cloud or '—'}\n"
        f"Scale: {snap.scale_availability or '—'}\n"
        f"Constraints: {snap.tech_constraints or '—'}\n"
        f"Already answered codes: {', '.join(sorted(snap.answered_codes)) or 'none'}\n"
        f"Captured requirement snippets: {'; '.join(snap.requirement_texts[:8]) or 'none'}\n"
    )


def _normalize_followup_item(item: dict[str, Any], *, existing: set[str]) -> Any | None:
    from app.modules.requirements.gaps import Gap as GapCls

    code = str(item.get("code") or item.get("ai_code") or "").strip()
    prompt = str(item.get("prompt") or "").strip()
    category = str(item.get("category") or "requirements").strip() or "requirements"
    if not code or not prompt:
        return None
    if not code.startswith("ai_"):
        code = f"ai_{code}"
    if code in existing:
        return None
    if category not in {"requirements", "nfrs", "security"}:
        return None
    return GapCls(code=code, prompt=prompt, category=category)


def _gap_line(g: Gap, snap: IntakeSnapshot) -> str:
    prior = (snap.answered_answers.get(g.code) or "").strip()
    if prior and g.code not in snap.answered_codes:
        return (
            f"- {g.code}: {g.prompt} [{g.category}] "
            f'(previously attempted but insufficient: "{prior[:200]}" — ask this from a '
            f"genuinely different angle, not the same question reworded)"
        )
    return f"- {g.code}: {g.prompt} [{g.category}]"


def assist_interview(
    gateway: AIGateway,
    snap: IntakeSnapshot,
    gaps: list[Gap],
    *,
    allow_followup: bool,
    exclude_codes: set[str] | None = None,
) -> InterviewAssistResult:
    """Rewrite structural gaps for this problem + decide whether one more
    follow-up would help, or whether there's already enough to design a
    concrete solution."""
    from app.modules.requirements.gaps import Gap as GapCls

    open_codes = [g.code for g in gaps]
    excluded = set(exclude_codes or ()) | set(open_codes) | set(snap.answered_codes)
    system = (
        "You run a requirements-confirmation interview for a solution architect. "
        "Sound like a sharp colleague. Return JSON only.\n"
        "Mission: understand THIS problem well enough to design real solutions — "
        "not to tick a standard NFR checklist.\n"
        "Rules:\n"
        "1) intro: 1-2 sentences. Name the system and the problem you are clarifying. "
        "No welcome fluff.\n"
        "2) rewrites: REQUIRED for EVERY open structural gap code listed. Rephrase "
        "so each is SPECIFIC to the objective and problem statement (name actors, "
        "workflows, or data if known). Keep the original intent (e.g. RTO still asks "
        "for recovery targets) but never leave a Clarify: stub or a generic textbook "
        "question. If a gap is marked as previously attempted but insufficient, your "
        "rewrite MUST approach it from a different angle — do not just reword the same ask.\n"
        "3) sufficient: true if you already have enough — from the objective/problem, "
        "structural answers, and prior follow-ups — to design a concrete, specific "
        "solution (not generic categories). false if one more question would "
        "meaningfully sharpen the solution.\n"
        "4) followup: null when sufficient is true, or when told no followup is allowed. "
        "Otherwise exactly ONE new question — the single most valuable thing still "
        "missing to ground a concrete solution: domain rules, integrating systems, "
        "data lifecycle, ownership, failure/degraded modes, compliance, or measurable "
        "success criteria. Code MUST start with ai_ and MUST NOT duplicate excluded codes.\n"
        "Categories: requirements | nfrs | security.\n"
        "Ground in stated cloud/stack only when evidenced. Never invent vendors."
    )
    gap_lines = "\n".join(_gap_line(g, snap) for g in gaps) or "- (none)"
    excluded_sorted = ", ".join(sorted(excluded)) or "none"
    followup_note = (
        "You may propose one followup if sufficient is false."
        if allow_followup
        else "Do not propose a followup (followup must be null) even if sufficient is "
        "false — at the safety ceiling for follow-up questions."
    )
    user = (
        f"{_project_blurb(snap)}\n"
        f"Open structural gaps to rewrite (safety-net checklist — make them problem-specific):\n"
        f"{gap_lines}\n\n"
        f"Return rewrites for codes: {', '.join(open_codes) or 'none'}.\n"
        f"{followup_note} Excluded codes for followup: {excluded_sorted}."
    )
    try:
        raw = gateway.complete_json(
            [ChatMessage(role="system", content=system), ChatMessage(role="user", content=user)],
            INTERVIEW_ASSIST_SCHEMA,
            timeout_s=60,
        )
    except Exception as exc:
        return InterviewAssistResult(status=as_ai_failure(exc))

    intro = str(raw.get("intro") or "").strip() or None
    rewrites_raw = raw.get("rewrites") or {}
    rewrites: dict[str, str] = {}
    if isinstance(rewrites_raw, dict):
        for code, prompt in rewrites_raw.items():
            p = str(prompt or "").strip()
            if code and p:
                rewrites[str(code)] = p

    sufficient = bool(raw.get("sufficient") or False)

    followups: list[GapCls] = []
    followup_raw = raw.get("followup")
    if allow_followup and not sufficient and isinstance(followup_raw, dict):
        gap = _normalize_followup_item(followup_raw, existing=set(excluded))
        if gap is not None:
            followups.append(gap)

    detail_parts = []
    if rewrites:
        detail_parts.append(f"rewrites={len(rewrites)}")
    if followups:
        detail_parts.append("followup=1")
    if sufficient:
        detail_parts.append("sufficient")
    if not allow_followup:
        detail_parts.append("followup_ceiling")
    if not detail_parts:
        detail_parts.append("empty_model_output")

    return InterviewAssistResult(
        intro=intro,
        rewrites=rewrites,
        followups=followups,
        sufficient=sufficient,
        status=AiAssistStatus(status="ok", detail=",".join(detail_parts)),
    )


def acknowledge_answer(
    gateway: AIGateway,
    snap: IntakeSnapshot,
    *,
    question_prompt: str,
    answer: str,
    next_question: str | None,
) -> tuple[str | None, AiAssistStatus]:
    """Short conversational acknowledgment after an interview answer."""
    system = (
        "You are Archavow's interview copilot. Return JSON with reply: "
        "1-2 sentences acknowledging how the answer clarifies the problem, then "
        "briefly teeing up the next question if provided. No markdown bullets. "
        "Do not introduce technologies, clouds, or frameworks that are not already "
        "evidenced in the project context or the answers provided."
    )
    user = (
        f"{_project_blurb(snap)}\n"
        f"Question asked: {question_prompt}\n"
        f"Architect answered: {answer}\n"
        f"Next question: {next_question or '(interview complete)'}\n"
    )
    try:
        raw = gateway.complete_json(
            [ChatMessage(role="system", content=system), ChatMessage(role="user", content=user)],
            ACK_SCHEMA,
            timeout_s=25,
        )
    except Exception as exc:
        return None, as_ai_failure(exc)
    reply = str(raw.get("reply") or "").strip()
    if not reply:
        return None, AiAssistStatus(status="failed", detail="empty_reply")
    return reply, AiAssistStatus(status="ok")


def suggest_answer_draft(
    gateway: AIGateway,
    snap: IntakeSnapshot,
    *,
    code: str,
    prompt: str,
) -> tuple[str | None, AiAssistStatus]:
    """Draft a plausible answer to one open interview question — a starting point
    for the architect to edit, never a fact asserted without their review."""
    system = (
        "You are Archavow's interview copilot. An architect is stuck on one "
        "question and wants a concrete starting draft grounded in THIS problem. "
        "Return JSON with suggestion: 2-4 sentences of plausible, decisive content "
        "for THIS question only. Prefer specifics implied by the objective/problem "
        "statement over generic NFR boilerplate. If a fact must be assumed "
        "(e.g. specific RTO minutes), pick an industry-typical default and say so "
        "briefly — never invent a vendor, cloud, or technology that isn't evidenced. "
        "This is a draft the architect will edit before submitting."
    )
    user = (
        f"{_project_blurb(snap)}\n"
        f"Question ({code}): {prompt}\n"
        "Draft an answer they can edit and submit."
    )
    try:
        raw = gateway.complete_json(
            [ChatMessage(role="system", content=system), ChatMessage(role="user", content=user)],
            ANSWER_SUGGESTION_SCHEMA,
            timeout_s=30,
        )
    except Exception as exc:
        return None, as_ai_failure(exc)
    suggestion = str(raw.get("suggestion") or "").strip()
    if not suggestion:
        return None, AiAssistStatus(status="failed", detail="empty_suggestion")
    return suggestion, AiAssistStatus(status="ok")
