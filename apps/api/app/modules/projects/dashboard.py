"""Project dashboard — lifecycle, score, decisions, risks."""

from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models import ArchitectureOptionRow, ArchitecturePackageRow
from app.modules.projects.lifecycle import ProjectLifecycle
from app.modules.projects.service import Project, _to_project, get_project_row


class DashboardOut(BaseModel):
    project: Project
    lifecycle: ProjectLifecycle
    continue_path: str
    quality_score: dict | None = None
    selected_option: dict | None = None
    decisions: list[dict] = Field(default_factory=list)
    open_risks: list[dict] = Field(default_factory=list)
    backlog: list[dict] = Field(default_factory=list)
    threats: list[dict] = Field(default_factory=list)
    package_status: str | None = None


def get_dashboard(db: Session, project_id: str) -> DashboardOut | None:
    row = get_project_row(db, project_id)
    if row is None:
        return None
    project = _to_project(row, db)
    assert project.lifecycle is not None
    life = project.lifecycle

    pkg = (
        db.query(ArchitecturePackageRow)
        .filter(ArchitecturePackageRow.project_id == row.id)
        .order_by(ArchitecturePackageRow.created_at.desc())
        .first()
    )
    selected = (
        db.query(ArchitectureOptionRow)
        .filter(
            ArchitectureOptionRow.project_id == row.id,
            ArchitectureOptionRow.selected.is_(True),
        )
        .first()
    )
    selected_option = None
    if selected is not None:
        selected_option = {
            "id": str(selected.id),
            "title": selected.title,
            "summary": selected.summary,
            "fit_score": selected.fit_score,
        }

    decisions: list[dict] = []
    open_risks: list[dict] = []
    backlog: list[dict] = []
    threats: list[dict] = []
    quality_score = None
    package_status = None
    if pkg is not None:
        package_status = pkg.status
        quality_score = dict(getattr(pkg, "quality_score", None) or {}) or None
        decisions = list(pkg.adrs or [])
        open_risks = [
            r
            for r in (pkg.risks or [])
            if str(r.get("severity", "")).lower() in {"high", "medium"}
        ]
        backlog = list(getattr(pkg, "backlog", None) or [])
        threats = list(getattr(pkg, "threats", None) or [])

    return DashboardOut(
        project=project,
        lifecycle=life,
        continue_path=life.continue_path,
        quality_score=quality_score,
        selected_option=selected_option,
        decisions=decisions,
        open_risks=open_risks,
        backlog=backlog,
        threats=threats,
        package_status=package_status,
    )
