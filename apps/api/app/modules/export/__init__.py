"""Export HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.export import service as export_service

router = APIRouter(prefix="/api/v1/projects", tags=["export"])


@router.post("/{project_id}/exports", status_code=201)
def post_export(
    project_id: str,
    payload: export_service.ExportCreate,
    db: Session = Depends(get_db),
) -> dict:
    result, err = export_service.create_export(db, project_id, payload)
    if err == "not_found":
        raise HTTPException(status_code=404, detail="project not found")
    if err == "no_package":
        raise HTTPException(
            status_code=409,
            detail="generate and select a package before exporting",
        )
    assert result is not None
    return {"data": result.model_dump()}


@router.get("/{project_id}/exports")
def get_exports(project_id: str, db: Session = Depends(get_db)) -> dict:
    runs = export_service.list_exports(db, project_id)
    if runs is None:
        raise HTTPException(status_code=404, detail="project not found")
    return {"data": [r.model_dump() for r in runs]}


@router.get("/{project_id}/exports/{export_id}")
def get_export(project_id: str, export_id: str, db: Session = Depends(get_db)) -> dict:
    run = export_service.get_export(db, project_id, export_id)
    if run is None:
        raise HTTPException(status_code=404, detail="export not found")
    return {"data": run.model_dump()}


@router.get("/{project_id}/exports/{export_id}/download")
def download_export(
    project_id: str, export_id: str, db: Session = Depends(get_db)
) -> Response:
    data = export_service.build_zip_bytes(db, project_id, export_id)
    if data is None:
        raise HTTPException(status_code=404, detail="export not found")
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="archavow-export-{export_id[:8]}.zip"'
        },
    )
