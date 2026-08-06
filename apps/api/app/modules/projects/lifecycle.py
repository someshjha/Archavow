"""Derive and maintain project workflow lifecycle from artifacts."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models import (
    ArchitectureOptionRow,
    ArchitecturePackageRow,
    ClarificationQuestionRow,
    ExportRunRow,
    ProjectRow,
    RequirementRow,
)

Stage = Literal["intake", "interview", "options", "package", "export"]

STAGE_LABELS: dict[Stage, str] = {
    "intake": "Onboarding",
    "interview": "Interview",
    "options": "Options",
    "package": "Package",
    "export": "Export",
}


class ProjectMilestones(BaseModel):
    intake_done: bool = True
    interview_started: bool = False
    interview_ready: bool = False
    options_ready: bool = False
    option_selected: bool = False
    package_ready: bool = False
    export_done: bool = False


class ProjectLifecycle(BaseModel):
    stage: Stage
    label: str
    continue_path: str
    milestones: ProjectMilestones = Field(default_factory=ProjectMilestones)


def _interview_ready_from_state(
    project: ProjectRow,
    *,
    answered_answers: dict[str, str],
    requirement_texts: list[str],
    intake_requirement_texts: list[str],
) -> bool:
    """Options unlock only when the completeness scorecard clears every floor.

    Same analysis the interview panel shows, so the CTA and the lifecycle can
    never disagree about whether the interview is done.
    """
    from app.modules.requirements.gaps import IntakeSnapshot, analyze_gaps

    snap = IntakeSnapshot(
        business_objective=project.business_objective or "",
        problem_statement=project.problem_statement or "",
        preferred_cloud=project.preferred_cloud or "",
        scale_availability=project.scale_availability or "",
        tech_constraints=project.tech_constraints or "",
        requirement_texts=requirement_texts,
        intake_requirement_texts=intake_requirement_texts,
        answered_answers=answered_answers,
    )
    return analyze_gaps(snap).completeness.ready


def _interview_ready(db: Session, project: ProjectRow) -> bool:
    answered_rows = (
        db.query(ClarificationQuestionRow)
        .filter(
            ClarificationQuestionRow.project_id == project.id,
            ClarificationQuestionRow.status.in_(("answered", "skipped")),
        )
        .all()
    )
    answered_answers = {
        q.code: (q.answer or "")
        for q in answered_rows
        if q.status == "answered" and q.answer
    }
    req_rows = (
        db.query(RequirementRow)
        .filter(RequirementRow.project_id == project.id)
        .all()
    )
    return _interview_ready_from_state(
        project,
        answered_answers=answered_answers,
        requirement_texts=[r.text for r in req_rows],
        intake_requirement_texts=[r.text for r in req_rows if r.source == "intake"],
    )


def _lifecycle_from_flags(
    project_id: str,
    *,
    interview_started: bool,
    interview_ready: bool,
    options_ready: bool,
    option_selected: bool,
    package_ready: bool,
    export_done: bool,
) -> ProjectLifecycle:
    milestones = ProjectMilestones(
        intake_done=True,
        interview_started=interview_started,
        interview_ready=interview_ready,
        options_ready=options_ready,
        option_selected=option_selected,
        package_ready=package_ready,
        export_done=export_done,
    )

    if export_done:
        stage: Stage = "export"
    elif package_ready:
        stage = "package"
    elif options_ready:
        stage = "options"
    elif interview_started:
        stage = "interview"
    else:
        stage = "intake"

    return ProjectLifecycle(
        stage=stage,
        label=STAGE_LABELS[stage],
        continue_path=_continue_path(project_id, milestones),
        milestones=milestones,
    )


def compute_lifecycle(db: Session, row: ProjectRow) -> ProjectLifecycle:
    return compute_lifecycles(db, [row])[row.id]


def compute_lifecycles(
    db: Session, rows: Sequence[ProjectRow]
) -> dict[uuid.UUID, ProjectLifecycle]:
    """Batch lifecycle for many projects (avoids N+1 on list endpoints)."""
    if not rows:
        return {}

    ids = [r.id for r in rows]
    by_id = {r.id: r for r in rows}

    questions = (
        db.query(ClarificationQuestionRow)
        .filter(ClarificationQuestionRow.project_id.in_(ids))
        .all()
    )
    questions_by: dict[uuid.UUID, list[ClarificationQuestionRow]] = defaultdict(list)
    for q in questions:
        questions_by[q.project_id].append(q)

    options = (
        db.query(ArchitectureOptionRow)
        .filter(ArchitectureOptionRow.project_id.in_(ids))
        .all()
    )
    options_by: dict[uuid.UUID, list[ArchitectureOptionRow]] = defaultdict(list)
    for o in options:
        options_by[o.project_id].append(o)

    package_pids = {
        pid
        for (pid,) in db.query(ArchitecturePackageRow.project_id)
        .filter(ArchitecturePackageRow.project_id.in_(ids))
        .distinct()
        .all()
    }
    export_pids = {
        pid
        for (pid,) in db.query(ExportRunRow.project_id)
        .filter(ExportRunRow.project_id.in_(ids))
        .distinct()
        .all()
    }

    requirements = (
        db.query(RequirementRow).filter(RequirementRow.project_id.in_(ids)).all()
    )
    reqs_by: dict[uuid.UUID, list[str]] = defaultdict(list)
    intake_reqs_by: dict[uuid.UUID, list[str]] = defaultdict(list)
    for r in requirements:
        reqs_by[r.project_id].append(r.text)
        if r.source == "intake":
            intake_reqs_by[r.project_id].append(r.text)

    out: dict[uuid.UUID, ProjectLifecycle] = {}
    for pid in ids:
        row = by_id[pid]
        qs = questions_by.get(pid, [])
        opts = options_by.get(pid, [])
        interview_started = len(qs) > 0
        answered_answers = {
            q.code: (q.answer or "")
            for q in qs
            if q.status == "answered" and q.answer
        }
        interview_ready = (
            _interview_ready_from_state(
                row,
                answered_answers=answered_answers,
                requirement_texts=reqs_by.get(pid, []),
                intake_requirement_texts=intake_reqs_by.get(pid, []),
            )
            if interview_started
            else False
        )
        out[pid] = _lifecycle_from_flags(
            str(pid),
            interview_started=interview_started,
            interview_ready=interview_ready,
            options_ready=len(opts) > 0,
            option_selected=any(o.selected for o in opts),
            package_ready=pid in package_pids,
            export_done=pid in export_pids,
        )
    return out


def _continue_path(project_id: str, m: ProjectMilestones) -> str:
    base = f"/projects/{project_id}"
    if not m.interview_started:
        return f"{base}/interview"
    if not m.interview_ready:
        return f"{base}/interview"
    if not m.options_ready or not m.option_selected or not m.package_ready:
        return f"{base}/options"
    if not m.export_done:
        return f"{base}/export"
    return f"{base}/package"
