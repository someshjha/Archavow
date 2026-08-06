"""Options + package HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.options import advisor as advisor_service
from app.modules.options import service as options_service

router = APIRouter(prefix="/api/v1/projects", tags=["options"])


@router.post("/{project_id}/options/generate")
def post_generate_options(project_id: str, db: Session = Depends(get_db)) -> dict:
    data = options_service.generate_options(db, project_id)
    if data is None:
        raise HTTPException(status_code=404, detail="project not found")
    return {
        "data": {
            "options": [o.model_dump() for o in data["options"]],
            "selected_option_id": data["selected_option_id"],
            "ai_assist": data.get("ai_assist") or {"status": "skipped"},
        }
    }


@router.get("/{project_id}/options")
def get_options(project_id: str, db: Session = Depends(get_db)) -> dict:
    data = options_service.list_options(db, project_id)
    if data is None:
        raise HTTPException(status_code=404, detail="project not found")
    return {
        "data": {
            "options": [o.model_dump() for o in data["options"]],
            "selected_option_id": data["selected_option_id"],
            "ai_assist": data.get("ai_assist") or {"status": "skipped"},
        }
    }


@router.post("/{project_id}/options/{option_id}/select")
def post_select(project_id: str, option_id: str, db: Session = Depends(get_db)) -> dict:
    data = options_service.select_option(db, project_id, option_id)
    if data is None:
        raise HTTPException(status_code=404, detail="project or option not found")
    return {
        "data": {
            "options": [o.model_dump() for o in data["options"]],
            "selected_option_id": data["selected_option_id"],
        }
    }


@router.post("/{project_id}/package/generate")
def post_package(project_id: str, db: Session = Depends(get_db)) -> dict:
    pkg, err = options_service.generate_package(db, project_id)
    if err == "not_found":
        raise HTTPException(status_code=404, detail="project not found")
    if err == "not_selected":
        raise HTTPException(
            status_code=409,
            detail="human gate: select an architecture option before generating the package",
        )
    assert pkg is not None
    return {"data": pkg.model_dump()}


@router.get("/{project_id}/package")
def get_package(project_id: str, db: Session = Depends(get_db)) -> dict:
    pkg = options_service.get_package(db, project_id)
    if pkg is None:
        raise HTTPException(status_code=404, detail="package not found")
    return {"data": pkg.model_dump()}


@router.post("/{project_id}/advisor/accept")
def post_advisor_accept(
    project_id: str,
    body: advisor_service.AdvisorAcceptIn,
    db: Session = Depends(get_db),
) -> dict:
    adr, adrs, err = advisor_service.accept_comparison(db, project_id, body)
    if err == "not_found":
        raise HTTPException(status_code=404, detail="project not found")
    if err == "invalid_options":
        raise HTTPException(status_code=400, detail="invalid option selection")
    if err == "package_not_found":
        raise HTTPException(
            status_code=409,
            detail="generate a package before accepting an ADR",
        )
    assert adr is not None and adrs is not None
    return {
        "data": {
            "adr": adr.model_dump(),
            "adrs": [a.model_dump() for a in adrs],
        }
    }
