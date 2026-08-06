"""Projects HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.projects.dashboard import get_dashboard
from app.modules.projects.service import (
    ProjectCreate,
    create_project,
    delete_project,
    get_project,
    list_projects,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", status_code=201)
def create(payload: ProjectCreate, db: Session = Depends(get_db)) -> dict:
    project = create_project(db, payload)
    return {"data": project.model_dump()}


@router.get("")
def list_all(db: Session = Depends(get_db)) -> dict:
    return {"data": [p.model_dump() for p in list_projects(db)]}


@router.get("/{project_id}/dashboard")
def dashboard(project_id: str, db: Session = Depends(get_db)) -> dict:
    data = get_dashboard(db, project_id)
    if data is None:
        raise HTTPException(status_code=404, detail="project not found")
    return {"data": data.model_dump()}


@router.get("/{project_id}")
def get_one(project_id: str, db: Session = Depends(get_db)) -> dict:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return {"data": project.model_dump()}


@router.delete("/{project_id}", status_code=204)
def delete_one(project_id: str, db: Session = Depends(get_db)) -> None:
    if not delete_project(db, project_id):
        raise HTTPException(status_code=404, detail="project not found")
