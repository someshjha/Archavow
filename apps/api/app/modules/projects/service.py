"""Projects — Postgres-backed with S1 intake fields + derived lifecycle."""

from __future__ import annotations

import re
import uuid

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db.models import ProjectRow, RequirementRow
from app.modules.projects.lifecycle import ProjectLifecycle, compute_lifecycle


def _clean_requirements(raw: list[str] | None) -> list[str]:
    """One requirement per entry, order preserved — story refs (R-001…) are positional."""
    if not raw:
        return []
    cleaned: list[str] = []
    for entry in raw:
        text = " ".join(str(entry).split())
        if not text:
            continue
        if len(text) > 2_000:
            raise ValueError("each requirement must be at most 2000 characters")
        cleaned.append(text)
    return cleaned


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=8_000)
    stack_tags: list[str] = Field(default_factory=list, max_length=32)
    business_objective: str | None = Field(default=None, max_length=8_000)
    problem_statement: str | None = Field(default=None, max_length=8_000)
    preferred_cloud: str | None = Field(default=None, max_length=64)
    scale_availability: str | None = Field(default=None, max_length=2_000)
    tech_constraints: str | None = Field(default=None, max_length=8_000)
    requirements: list[str] = Field(default_factory=list, max_length=200)

    @field_validator("requirements")
    @classmethod
    def _requirements(cls, raw: list[str]) -> list[str]:
        return _clean_requirements(raw)

    @field_validator("stack_tags")
    @classmethod
    def _tag_lengths(cls, tags: list[str]) -> list[str]:
        cleaned: list[str] = []
        for tag in tags:
            t = tag.strip()
            if not t:
                continue
            if len(t) > 64:
                raise ValueError("each stack_tag must be at most 64 characters")
            cleaned.append(t)
        return cleaned


class IntakeUpdate(BaseModel):
    business_objective: str | None = Field(default=None, max_length=8_000)
    problem_statement: str | None = Field(default=None, max_length=8_000)
    preferred_cloud: str | None = Field(default=None, max_length=64)
    scale_availability: str | None = Field(default=None, max_length=2_000)
    tech_constraints: str | None = Field(default=None, max_length=8_000)
    description: str | None = Field(default=None, max_length=8_000)
    stack_tags: list[str] | None = Field(default=None, max_length=32)
    requirements: list[str] | None = Field(default=None, max_length=200)

    @field_validator("requirements")
    @classmethod
    def _requirements(cls, raw: list[str] | None) -> list[str] | None:
        if raw is None:
            return None
        return _clean_requirements(raw)

    @field_validator("stack_tags")
    @classmethod
    def _tag_lengths(cls, tags: list[str] | None) -> list[str] | None:
        if tags is None:
            return None
        cleaned: list[str] = []
        for tag in tags:
            t = tag.strip()
            if not t:
                continue
            if len(t) > 64:
                raise ValueError("each stack_tag must be at most 64 characters")
            cleaned.append(t)
        return cleaned


class Project(BaseModel):
    id: str
    name: str
    description: str | None = None
    stack_tags: list[str] = Field(default_factory=list)
    business_objective: str | None = None
    problem_statement: str | None = None
    preferred_cloud: str | None = None
    scale_availability: str | None = None
    tech_constraints: str | None = None
    requirements: list[str] = Field(default_factory=list)
    lifecycle: ProjectLifecycle | None = None


def _to_project(
    row: ProjectRow,
    db: Session | None = None,
    *,
    lifecycle: ProjectLifecycle | None = None,
) -> Project:
    life = lifecycle
    reqs: list[str] = []
    if db is not None:
        life = life or compute_lifecycle(db, row)
        # Only on single-project reads; the list view passes a precomputed
        # lifecycle and no session precisely to avoid a query per row.
        reqs = [
            r.text
            for r in db.query(RequirementRow)
            .filter(RequirementRow.project_id == row.id, RequirementRow.source == "intake")
            .order_by(RequirementRow.created_at.asc())
            .all()
        ]
    return Project(
        id=str(row.id),
        name=row.name,
        description=row.description,
        stack_tags=list(row.stack_tags or []),
        business_objective=row.business_objective,
        problem_statement=row.problem_statement,
        preferred_cloud=row.preferred_cloud,
        scale_availability=row.scale_availability,
        tech_constraints=row.tech_constraints,
        requirements=reqs,
        lifecycle=life,
    )


def create_project(db: Session, payload: ProjectCreate) -> Project:
    row = ProjectRow(
        id=uuid.uuid4(),
        name=payload.name,
        description=payload.description,
        stack_tags=list(payload.stack_tags),
        business_objective=payload.business_objective,
        problem_statement=payload.problem_statement,
        preferred_cloud=payload.preferred_cloud,
        scale_availability=payload.scale_availability,
        tech_constraints=payload.tech_constraints,
    )
    db.add(row)
    _replace_intake_requirements(db, row.id, payload.requirements)
    db.commit()
    db.refresh(row)
    return _to_project(row, db)


def _replace_intake_requirements(
    db: Session, project_id: uuid.UUID, requirements: list[str] | None
) -> None:
    """Stated requirements live as `intake` rows so gap analysis, options, and the
    delivery backlog all read them from one place. Interview-sourced rows are left
    untouched — only the human-entered intake list is replaced."""
    if requirements is None:
        return
    db.query(RequirementRow).filter(
        RequirementRow.project_id == project_id,
        RequirementRow.source == "intake",
    ).delete(synchronize_session=False)
    for text in requirements:
        db.add(
            RequirementRow(
                id=uuid.uuid4(),
                project_id=project_id,
                kind=_requirement_kind(text),
                text=text,
                source="intake",
            )
        )


def _requirement_kind(text: str) -> str:
    low = text.lower()
    if re.search(r"\b(auth|encrypt|permission|role|gdpr|hipaa|pci|audit|consent|residency)\b", low):
        return "security"
    if re.search(
        r"\b(availability|latency|throughput|rto|rpo|scale|uptime|performance|concurrent|sla)\b",
        low,
    ):
        return "nfr"
    return "fr"


def list_projects(db: Session) -> list[Project]:
    from app.modules.projects.lifecycle import compute_lifecycles

    rows = db.query(ProjectRow).order_by(ProjectRow.created_at.desc()).all()
    lives = compute_lifecycles(db, rows)
    return [_to_project(r, lifecycle=lives[r.id]) for r in rows]


def get_project(db: Session, project_id: str) -> Project | None:
    row = get_project_row(db, project_id)
    return _to_project(row, db) if row else None


def delete_project(db: Session, project_id: str) -> bool:
    """Hard-delete a project. Child rows cascade via FK ondelete=CASCADE."""
    row = get_project_row(db, project_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def get_project_row(db: Session, project_id: str) -> ProjectRow | None:
    try:
        uid = uuid.UUID(project_id)
    except ValueError:
        return None
    return db.get(ProjectRow, uid)


def update_intake(db: Session, project_id: str, payload: IntakeUpdate) -> Project | None:
    row = get_project_row(db, project_id)
    if row is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    # Requirements are rows, not a column on the project.
    requirements = data.pop("requirements", None)
    for key, value in data.items():
        setattr(row, key, value)
    db.add(row)
    _replace_intake_requirements(db, row.id, requirements)
    db.commit()
    db.refresh(row)
    return _to_project(row, db)


def reset(db: Session) -> None:
    db.query(ProjectRow).delete()
    db.commit()
