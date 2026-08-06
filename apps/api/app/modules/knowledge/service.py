"""Knowledge ingest + keyword/hybrid search.

This module is kept as a thin backward-compatible re-export. The
implementation now lives in sibling modules:
- schemas.py — request/response Pydantic models
- seed.py — seed corpus ingestion
- ingest.py — document ingestion (chunking + embedding)
- retrieval.py — keyword/hybrid search
- ask.py — ask-the-knowledge-base flow
"""

from __future__ import annotations

from app.modules.knowledge.ask import ask, capture_project_decision
from app.modules.knowledge.ingest import ingest_document, list_documents
from app.modules.knowledge.retrieval import _keyword_score, _phrase_boost, _tokenize, search
from app.modules.knowledge.schemas import (
    AskRequest,
    AskResult,
    DocumentCreate,
    DocumentOut,
    SearchHit,
    SearchRequest,
    SearchResult,
    SourceClass,
)
from app.modules.knowledge.seed import ensure_seeded, seed_documents

__all__ = [
    "SourceClass",
    "DocumentCreate",
    "DocumentOut",
    "SearchHit",
    "SearchRequest",
    "SearchResult",
    "AskRequest",
    "AskResult",
    "list_documents",
    "seed_documents",
    "ensure_seeded",
    "ingest_document",
    "search",
    "ask",
    "capture_project_decision",
    # Private helpers still imported directly by tests.
    "_tokenize",
    "_keyword_score",
    "_phrase_boost",
]
