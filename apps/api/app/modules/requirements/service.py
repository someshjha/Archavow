"""Requirements + interview services."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field
from sqlalchemy import case, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import Case

from typing import Literal

from app.ai.assist import (
    acknowledge_answer,
    as_ai_failure,
    assist_interview,
    suggest_answer_draft,
)
from app.ai.config import resolve_effective_ai_config
from app.ai.gateway import build_gateway
from app.db.models import ClarificationQuestionRow, ProjectRow, RequirementRow
from app.modules.projects.service import get_project_row
from app.modules.requirements.gaps import (
    CODE_ORDER,
    GapAnalysis,
    IntakeSnapshot,
    analyze_gaps,
    answer_satisfies,
    is_placeholder_answer,
    kind_from_category,
    matches_suggestion_template,
    pick_next_code,
    project_close,
    suggestion_template,
)
from app.modules.settings import service as settings_service


class RequirementOut(BaseModel):
    id: str
    kind: str
    text: str
    source: str


class QuestionOut(BaseModel):
    id: str
    code: str
    prompt: str
    category: str
    status: str
    answer: str | None = None


class CompletenessCategoryOut(BaseModel):
    key: str
    label: str
    score: int
    floor: int
    closed: int
    total: int
    open_codes: list[str] = Field(default_factory=list)
    open_labels: list[str] = Field(default_factory=list)


class UnlockCheckOut(BaseModel):
    key: str
    label: str
    value: int
    target: int
    ok: bool


class CompletenessOut(BaseModel):
    overall: int
    scope: int
    story_readiness: int
    reliability: int
    security_compliance: int
    delivery: int
    categories: list[CompletenessCategoryOut] = Field(default_factory=list)
    ready: bool = False
    unlock: list[UnlockCheckOut] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    captured: list[str] = Field(default_factory=list)


class NextImpactOut(BaseModel):
    """Exact scorecard movement the active question is worth, for the answer box."""

    code: str
    category_key: str
    category_label: str
    category_from: int
    category_to: int
    overall_from: int
    overall_to: int


class AnswerIn(BaseModel):
    question_id: str
    answer: str = Field(min_length=1, max_length=8_000)


class SuggestIn(BaseModel):
    question_id: str


class SuggestionOut(BaseModel):
    suggestion: str
    source: Literal["ai", "template"]
    ai_assist: dict


class AnswerValidationError(ValueError):
    """Interview answer is empty, placeholder, or lacks required evidence."""


# Purely defensive ceiling on AI-generated follow-ups (open + answered), in
# case the model never reports sufficient=true. Not a product-facing limit —
# the interview stops on its own once assist_interview signals sufficiency.
MAX_AI_FOLLOWUPS_SAFETY = 20


def _get_code_sort_expression() -> Case:
    """Return a CASE expression for ordering codes in the desired sequence.

    Uses CODE_ORDER from gap_analyze to ensure consistency with checks list order.
    Provides deterministic secondary sort when multiple ClarificationQuestionRow have
    identical created_at timestamps (common in same-transaction batch inserts).
    """
    whens = [(ClarificationQuestionRow.code == code, idx) for idx, code in enumerate(CODE_ORDER)]
    return case(*whens, else_=len(CODE_ORDER))


def _q_out(row: ClarificationQuestionRow) -> QuestionOut:
    return QuestionOut(
        id=str(row.id),
        code=row.code,
        prompt=row.prompt,
        category=row.category,
        status=row.status,
        answer=row.answer,
    )


def list_requirements(db: Session, project_id: str) -> list[RequirementOut]:
    uid = uuid.UUID(project_id)
    rows = (
        db.query(RequirementRow)
        .filter(RequirementRow.project_id == uid)
        .order_by(RequirementRow.created_at.asc())
        .all()
    )
    return [
        RequirementOut(id=str(r.id), kind=r.kind, text=r.text, source=r.source) for r in rows
    ]


def _snapshot(db: Session, project_id: str) -> IntakeSnapshot | None:
    row = get_project_row(db, project_id)
    if row is None:
        return None
    reqs = list_requirements(db, project_id)
    # Includes rejected-but-attempted answers on still-open questions (not just
    # genuinely satisfying ones) — IntakeSnapshot.answered_codes independently
    # re-validates via answer_satisfies, so this cannot make an unsatisfied gap
    # look satisfied; it only gives AI rewrites something real to reference.
    answered_answers = {
        q.code: (q.answer or "")
        for q in db.query(ClarificationQuestionRow)
        .filter(ClarificationQuestionRow.project_id == row.id)
        .all()
        if q.answer
    }
    return IntakeSnapshot(
        business_objective=row.business_objective or "",
        problem_statement=row.problem_statement or "",
        preferred_cloud=row.preferred_cloud or "",
        scale_availability=row.scale_availability or "",
        tech_constraints=row.tech_constraints or "",
        requirement_texts=[r.text for r in reqs],
        intake_requirement_texts=[r.text for r in reqs if r.source == "intake"],
        answered_answers=answered_answers,
    )


def _completeness_out(
    analysis: GapAnalysis, *, gap_codes: list[str] | None = None
) -> CompletenessOut:
    comp = analysis.completeness
    return CompletenessOut(
        overall=comp.overall,
        scope=comp.scope,
        story_readiness=comp.story_readiness,
        reliability=comp.reliability,
        security_compliance=comp.security_compliance,
        delivery=comp.delivery,
        categories=[
            CompletenessCategoryOut(
                key=c.key,
                label=c.label,
                score=c.score,
                floor=c.floor,
                closed=c.closed,
                total=c.total,
                open_codes=list(c.open_codes),
                open_labels=list(c.open_labels),
            )
            for c in comp.categories
        ],
        ready=comp.ready,
        unlock=[
            UnlockCheckOut(
                key=u.key, label=u.label, value=u.value, target=u.target, ok=u.ok
            )
            for u in comp.unlock
        ],
        gaps=gap_codes if gap_codes is not None else [g.code for g in analysis.gaps],
        captured=list(analysis.captured),
    )


def _active_question(
    questions: list[QuestionOut], analysis: GapAnalysis
) -> QuestionOut | None:
    """Ask from the weakest category first so the interview converges on the gate.

    Falls back to list order (CODE_ORDER) when nothing open maps to a category,
    which is the case once only AI follow-ups remain.
    """
    open_questions = [q for q in questions if q.status == "open"]
    if not open_questions:
        return None
    scores = {c.key: c.score for c in analysis.completeness.categories}
    code = pick_next_code([q.code for q in open_questions], scores)
    if code is None:
        return open_questions[0]
    return next((q for q in open_questions if q.code == code), open_questions[0])


def _next_impact(
    active: QuestionOut | None, analysis: GapAnalysis
) -> NextImpactOut | None:
    if active is None:
        return None
    projection = project_close(active.code, analysis.completeness.categories)
    if projection is None:
        return None
    return NextImpactOut(
        code=active.code,
        category_key=projection.category_key,
        category_label=projection.category_label,
        category_from=projection.category_from,
        category_to=projection.category_to,
        overall_from=projection.overall_from,
        overall_to=projection.overall_to,
    )


def completeness_payload(db: Session, project_id: str) -> CompletenessOut | None:
    snap = _snapshot(db, project_id)
    if snap is None:
        return None
    return _completeness_out(analyze_gaps(snap))


def analyze_interview(db: Session, project_id: str) -> dict | None:
    row = get_project_row(db, project_id)
    if row is None:
        return None

    # Lock the project row first so concurrent first-analyze (empty questions)
    # cannot both miss existing rows and insert duplicate codes.
    locked = (
        db.query(ProjectRow)
        .filter(ProjectRow.id == row.id)
        .with_for_update()
        .first()
    )
    if locked is None:
        return None

    existing_rows = (
        db.query(ClarificationQuestionRow)
        .filter(ClarificationQuestionRow.project_id == row.id)
        .with_for_update()
        .all()
    )
    existing = {q.code: q for q in existing_rows}
    persisted_codes = set(existing.keys())
    existing_ai_count = sum(1 for code in persisted_codes if code.startswith("ai_"))
    allow_followup = existing_ai_count < MAX_AI_FOLLOWUPS_SAFETY

    snap = _snapshot(db, project_id)
    assert snap is not None
    analysis = analyze_gaps(snap)

    ai_assist = {"status": "skipped", "detail": None}
    intro: str | None = None
    try:
        cfg = resolve_effective_ai_config(overrides=settings_service.get_overrides(db))
        gateway = build_gateway(cfg)
        assist = assist_interview(
            gateway,
            snap,
            analysis.gaps,
            allow_followup=allow_followup,
            exclude_codes=persisted_codes,
        )
        ai_assist = assist.status.model_dump()
        intro = assist.intro
        for gap in analysis.gaps:
            if gap.code in assist.rewrites:
                gap.prompt = assist.rewrites[gap.code]
        analysis.gaps.extend(assist.followups)
    except Exception as exc:
        ai_assist = as_ai_failure(exc).model_dump()

    # Upsert open gaps; reopen answered questions that still lack evidence
    open_codes = {g.code for g in analysis.gaps} | {
        code for code in persisted_codes if code.startswith("ai_")
    }
    for gap in analysis.gaps:
        if gap.code in existing:
            q = existing[gap.code]
            if q.status == "answered" and not answer_satisfies(gap.code, q.answer or ""):
                q.status = "open"
                q.prompt = gap.prompt
                q.category = gap.category
                db.add(q)
            elif q.status != "answered":
                q.prompt = gap.prompt
                q.category = gap.category
                q.status = "open"
                db.add(q)
        else:
            db.add(
                ClarificationQuestionRow(
                    id=uuid.uuid4(),
                    project_id=row.id,
                    code=gap.code,
                    prompt=gap.prompt,
                    category=gap.category,
                    status="open",
                )
            )

    # Drop obsolete structural gaps satisfied by intake — never delete AI follow-ups
    for code, q in existing.items():
        if code not in open_codes and q.status == "open" and not code.startswith("ai_"):
            db.delete(q)

    db.commit()

    questions = (
        db.query(ClarificationQuestionRow)
        .filter(ClarificationQuestionRow.project_id == row.id)
        .order_by(_get_code_sort_expression().asc(), ClarificationQuestionRow.created_at.asc())
        .all()
    )
    comp = _completeness_out(
        analysis,
        gap_codes=[g.code for g in analysis.gaps if not g.code.startswith("ai_")],
    )
    q_out = [_q_out(q) for q in questions]
    active = _active_question(q_out, analysis)
    return {
        "questions": q_out,
        "completeness": comp,
        "active_question": active,
        "next_impact": _next_impact(active, analysis),
        "ai_assist": ai_assist,
        "intro": intro,
    }


def get_interview(db: Session, project_id: str) -> dict | None:
    row = get_project_row(db, project_id)
    if row is None:
        return None
    questions = (
        db.query(ClarificationQuestionRow)
        .filter(ClarificationQuestionRow.project_id == row.id)
        .order_by(_get_code_sort_expression().asc(), ClarificationQuestionRow.created_at.asc())
        .all()
    )
    if not questions:
        return analyze_interview(db, project_id)
    snap = _snapshot(db, project_id)
    assert snap is not None
    analysis = analyze_gaps(snap)
    q_out = [_q_out(q) for q in questions]
    active = _active_question(q_out, analysis)
    return {
        "questions": q_out,
        "completeness": _completeness_out(analysis),
        "active_question": active,
        "next_impact": _next_impact(active, analysis),
        "ai_assist": {"status": "skipped", "detail": "cached_interview"},
    }


def answer_question(db: Session, project_id: str, payload: AnswerIn) -> dict | None:
    row = get_project_row(db, project_id)
    if row is None:
        return None
    try:
        qid = uuid.UUID(payload.question_id)
    except ValueError:
        return None

    # Lock the question row so concurrent submits serialize before upsert
    question = (
        db.query(ClarificationQuestionRow)
        .filter(
            ClarificationQuestionRow.id == qid,
            ClarificationQuestionRow.project_id == row.id,
        )
        .with_for_update()
        .first()
    )
    if question is None:
        return None

    asked_prompt = question.prompt
    answer_text = payload.answer.strip()
    snap = _snapshot(db, project_id)
    assert snap is not None
    if matches_suggestion_template(question.code, answer_text, snap):
        question.answer = answer_text
        db.add(question)
        db.commit()
        raise AnswerValidationError(
            "Edit the draft before sending — an unedited suggestion cannot become "
            f"project evidence (code={question.code})."
        )
    if is_placeholder_answer(answer_text) or not answer_satisfies(question.code, answer_text):
        # Keep the attempt (status stays "open") so a later AI rewrite can
        # reference it instead of repeating the identical question.
        question.answer = answer_text
        db.add(question)
        db.commit()
        raise AnswerValidationError(
            "Answer is a placeholder or lacks the evidence this question requires "
            f"(code={question.code})."
        )

    question.status = "answered"
    question.answer = answer_text
    db.add(question)

    source = f"interview:{question.code}"
    kind = kind_from_category(question.category)
    values = {
        "id": uuid.uuid4(),
        "project_id": row.id,
        "kind": kind,
        "text": answer_text,
        "source": source,
    }
    conflict_set = {"text": answer_text, "kind": kind}
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        stmt = (
            sqlite_insert(RequirementRow)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["project_id", "source"],
                index_where=text("source LIKE 'interview:%'"),
                set_=conflict_set,
            )
        )
    else:
        stmt = (
            pg_insert(RequirementRow)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["project_id", "source"],
                index_where=text("source LIKE 'interview:%'"),
                set_=conflict_set,
            )
        )
    db.execute(stmt)
    db.commit()
    db.refresh(question)

    state = analyze_interview(db, project_id)
    assert state is not None
    state["question"] = _q_out(question)

    ai_reply: str | None = None
    try:
        snap = _snapshot(db, project_id)
        assert snap is not None
        cfg = resolve_effective_ai_config(overrides=settings_service.get_overrides(db))
        gateway = build_gateway(cfg)
        next_q = state["active_question"].prompt if state.get("active_question") else None
        ai_reply, ack_status = acknowledge_answer(
            gateway,
            snap,
            question_prompt=asked_prompt,
            answer=answer_text,
            next_question=next_q,
        )
        if ack_status.status == "ok" and ai_reply:
            state["ai_reply"] = ai_reply
        else:
            state["ai_reply"] = None
            # Keep analyze status; attach ack detail only if analyze was ok
            if state.get("ai_assist", {}).get("status") == "ok" and ack_status.status == "failed":
                state["ai_assist"] = {
                    **state["ai_assist"],
                    "detail": f"{state['ai_assist'].get('detail')};ack_failed",
                }
    except Exception as exc:
        as_ai_failure(exc)
        state["ai_reply"] = None

    return state


def suggest_answer(db: Session, project_id: str, payload: SuggestIn) -> SuggestionOut | None:
    """Draft answer for one open question — AI when available, deterministic
    template otherwise. Always a starting point the architect edits, never
    auto-submitted."""
    row = get_project_row(db, project_id)
    if row is None:
        return None
    try:
        qid = uuid.UUID(payload.question_id)
    except ValueError:
        return None
    question = (
        db.query(ClarificationQuestionRow)
        .filter(
            ClarificationQuestionRow.id == qid,
            ClarificationQuestionRow.project_id == row.id,
        )
        .first()
    )
    if question is None:
        return None

    snap = _snapshot(db, project_id)
    assert snap is not None

    draft: str | None = None
    ai_status = {"status": "skipped", "detail": None}
    try:
        cfg = resolve_effective_ai_config(overrides=settings_service.get_overrides(db))
        gateway = build_gateway(cfg)
        draft, status = suggest_answer_draft(
            gateway, snap, code=question.code, prompt=question.prompt
        )
        ai_status = status.model_dump()
    except Exception as exc:
        ai_status = as_ai_failure(exc).model_dump()

    if draft:
        return SuggestionOut(suggestion=draft, source="ai", ai_assist=ai_status)

    template = suggestion_template(question.code, snap)
    fallback = template or (
        "No draft available for this question — answer from what you know, "
        "or say what's still undecided."
    )
    return SuggestionOut(suggestion=fallback, source="template", ai_assist=ai_status)
