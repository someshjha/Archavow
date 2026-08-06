"""Export service — assemble package artifacts into folder/zip payloads."""

from __future__ import annotations

import io
import uuid
import zipfile

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models import (
    ArchitectureOptionRow,
    ArchitecturePackageRow,
    ExportRunRow,
    RequirementRow,
)
from app.modules.export.packager import build_export_files
from app.modules.projects.service import _to_project, get_project_row


class ExportCreate(BaseModel):
    layout: str = Field(default="folder", pattern="^(folder|zip)$")
    include_hld: bool = True
    include_mermaid: bool = True
    include_adrs: bool = True
    include_risks: bool = True
    include_project_json: bool = True


class ExportFileOut(BaseModel):
    path: str
    content: str


class ExportOut(BaseModel):
    id: str
    layout: str
    status: str
    includes: dict
    files: list[ExportFileOut] = Field(default_factory=list)


class ExportSummary(BaseModel):
    id: str
    layout: str
    status: str
    includes: dict
    file_count: int


def _latest_package(db: Session, project_id: uuid.UUID) -> ArchitecturePackageRow | None:
    return (
        db.query(ArchitecturePackageRow)
        .filter(ArchitecturePackageRow.project_id == project_id)
        .order_by(ArchitecturePackageRow.created_at.desc())
        .first()
    )


def _selected_option(db: Session, project_id: uuid.UUID) -> ArchitectureOptionRow | None:
    return (
        db.query(ArchitectureOptionRow)
        .filter(
            ArchitectureOptionRow.project_id == project_id,
            ArchitectureOptionRow.selected.is_(True),
        )
        .first()
    )


def create_export(
    db: Session, project_id: str, payload: ExportCreate
) -> tuple[ExportOut | None, str | None]:
    """Returns (export, error). error='no_package' → 409."""
    row = get_project_row(db, project_id)
    if row is None:
        return None, "not_found"

    pkg = _latest_package(db, row.id)
    if pkg is None:
        return None, "no_package"

    opt = _selected_option(db, row.id)
    project = _to_project(row, db).model_dump()
    # Story traceability refs (R-001…) are positional over the requirements stated
    # at intake, so the export must carry that same list and ordering.
    project["requirements"] = [
        r.text
        for r in db.query(RequirementRow)
        .filter(RequirementRow.project_id == row.id, RequirementRow.source == "intake")
        .order_by(RequirementRow.created_at.asc())
        .all()
    ]
    package = {
        "id": str(pkg.id),
        "status": pkg.status,
        "option_id": str(pkg.option_id),
        "hld_markdown": pkg.hld_markdown,
        "mermaid": pkg.mermaid,
        "mermaid_sequence": getattr(pkg, "mermaid_sequence", None) or "",
        "mermaid_deploy": getattr(pkg, "mermaid_deploy", None) or "",
        "mermaid_container": getattr(pkg, "mermaid_container", None) or "",
        "adrs": list(pkg.adrs or []),
        "risks": list(pkg.risks or []),
        "citations": list(pkg.citations or []),
        "quality_score": dict(getattr(pkg, "quality_score", None) or {}),
        "backlog": list(getattr(pkg, "backlog", None) or []),
        "epics": list(getattr(pkg, "epics", None) or []),
        "threats": list(getattr(pkg, "threats", None) or []),
        "documents": dict(getattr(pkg, "documents", None) or {}),
        "retrieval_status": pkg.retrieval_status,
        "provenance": dict(pkg.provenance or {}),
    }
    selected = None
    if opt is not None:
        selected = {
            "id": str(opt.id),
            "title": opt.title,
            "summary": opt.summary,
            "key": opt.key,
        }

    files = build_export_files(
        project=project,
        package=package,
        selected_option=selected,
        include_hld=payload.include_hld,
        include_mermaid=payload.include_mermaid,
        include_adrs=payload.include_adrs,
        include_risks=payload.include_risks,
        include_project_json=payload.include_project_json,
    )
    includes = payload.model_dump()
    run = ExportRunRow(
        id=uuid.uuid4(),
        project_id=row.id,
        layout=payload.layout,
        status="ready",
        includes=includes,
        files=files,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return (
        ExportOut(
            id=str(run.id),
            layout=run.layout,
            status=run.status,
            includes=dict(run.includes or {}),
            files=[ExportFileOut(**f) for f in (run.files or [])],
        ),
        None,
    )


def list_exports(db: Session, project_id: str) -> list[ExportSummary] | None:
    row = get_project_row(db, project_id)
    if row is None:
        return None
    runs = (
        db.query(ExportRunRow)
        .filter(ExportRunRow.project_id == row.id)
        .order_by(ExportRunRow.created_at.desc())
        .all()
    )
    return [
        ExportSummary(
            id=str(r.id),
            layout=r.layout,
            status=r.status,
            includes=dict(r.includes or {}),
            file_count=len(r.files or []),
        )
        for r in runs
    ]


def get_export(db: Session, project_id: str, export_id: str) -> ExportOut | None:
    row = get_project_row(db, project_id)
    if row is None:
        return None
    try:
        eid = uuid.UUID(export_id)
    except ValueError:
        return None
    run = db.get(ExportRunRow, eid)
    if run is None or run.project_id != row.id:
        return None
    return ExportOut(
        id=str(run.id),
        layout=run.layout,
        status=run.status,
        includes=dict(run.includes or {}),
        files=[ExportFileOut(**f) for f in (run.files or [])],
    )


def build_zip_bytes(db: Session, project_id: str, export_id: str) -> bytes | None:
    export = get_export(db, project_id, export_id)
    if export is None:
        return None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in export.files:
            zf.writestr(f.path, f.content)
    return buf.getvalue()
