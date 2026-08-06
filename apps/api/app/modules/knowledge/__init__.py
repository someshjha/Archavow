"""Knowledge HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.knowledge import service as knowledge_service

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.get("/documents")
def get_documents(
    include_seed: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> dict:
    docs = knowledge_service.list_documents(db, include_seed=include_seed)
    return {"data": [d.model_dump() for d in docs]}


@router.post("/documents", status_code=201)
def post_document(payload: knowledge_service.DocumentCreate, db: Session = Depends(get_db)) -> dict:
    doc = knowledge_service.ingest_document(db, payload)
    return {"data": doc.model_dump()}


@router.post("/seed", status_code=201)
def post_seed(db: Session = Depends(get_db)) -> dict:
    # Ingest any new/changed seed files (content-hash idempotent)
    created = knowledge_service.seed_documents(db)
    return {
        "data": {
            "created": [d.model_dump() for d in created],
            "count": len(created),
        }
    }


@router.post("/search")
def post_search(payload: knowledge_service.SearchRequest, db: Session = Depends(get_db)) -> dict:
    result = knowledge_service.search(db, payload)
    return {"data": result.model_dump()}


@router.post("/ask")
def post_ask(payload: knowledge_service.AskRequest, db: Session = Depends(get_db)) -> dict:
    result = knowledge_service.ask(db, payload)
    return {"data": result.model_dump()}
