"""Requirements / interview HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.projects.service import IntakeUpdate, update_intake
from app.modules.requirements import service as req_service

router = APIRouter(prefix="/api/v1/projects", tags=["requirements"])


def _interview_payload(state: dict) -> dict:
    impact = state.get("next_impact")
    return {
        "questions": [q.model_dump() for q in state["questions"]],
        "completeness": state["completeness"].model_dump(),
        "active_question": (
            state["active_question"].model_dump() if state["active_question"] else None
        ),
        "next_impact": impact.model_dump() if impact else None,
        "ai_assist": state.get("ai_assist") or {"status": "skipped"},
        "intro": state.get("intro"),
    }


@router.put("/{project_id}/intake")
def put_intake(project_id: str, payload: IntakeUpdate, db: Session = Depends(get_db)) -> dict:
    project = update_intake(db, project_id, payload)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return {"data": project.model_dump()}


@router.get("/{project_id}/requirements")
def get_requirements(project_id: str, db: Session = Depends(get_db)) -> dict:
    from app.modules.projects.service import get_project

    if get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    return {"data": [r.model_dump() for r in req_service.list_requirements(db, project_id)]}


@router.post("/{project_id}/interview/analyze")
def post_analyze(project_id: str, db: Session = Depends(get_db)) -> dict:
    state = req_service.analyze_interview(db, project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="project not found")
    return {"data": _interview_payload(state)}


@router.get("/{project_id}/interview")
def get_interview(project_id: str, db: Session = Depends(get_db)) -> dict:
    state = req_service.get_interview(db, project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="project not found")
    return {"data": _interview_payload(state)}


@router.post("/{project_id}/interview/answer")
def post_answer(
    project_id: str,
    payload: req_service.AnswerIn,
    db: Session = Depends(get_db),
) -> dict:
    try:
        state = req_service.answer_question(db, project_id, payload)
    except req_service.AnswerValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if state is None:
        raise HTTPException(status_code=404, detail="project or question not found")
    return {
        "data": {
            **_interview_payload(state),
            "question": state["question"].model_dump(),
            "ai_reply": state.get("ai_reply"),
        }
    }


@router.post("/{project_id}/interview/suggest")
def post_suggest(
    project_id: str,
    payload: req_service.SuggestIn,
    db: Session = Depends(get_db),
) -> dict:
    out = req_service.suggest_answer(db, project_id, payload)
    if out is None:
        raise HTTPException(status_code=404, detail="project or question not found")
    return {"data": out.model_dump()}


@router.get("/{project_id}/completeness")
def get_completeness(project_id: str, db: Session = Depends(get_db)) -> dict:
    body = req_service.completeness_payload(db, project_id)
    if body is None:
        raise HTTPException(status_code=404, detail="project not found")
    return {"data": body.model_dump()}
