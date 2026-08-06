"""Knowledge module Pydantic schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SourceClass = Literal["org", "seed", "project"]


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    content: str = Field(min_length=1, max_length=512_000)
    source_class: SourceClass = "org"
    source_key: str | None = Field(default=None, max_length=512)


class DocumentOut(BaseModel):
    id: str
    title: str
    source_class: str
    chunk_count: int
    status: str
    content_hash: str
    embedding_model: str | None = None


class SearchHit(BaseModel):
    document_id: str
    chunk_id: str
    title: str
    source_class: str
    text: str
    score: float
    citation: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4_000)
    limit: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    hits: list[SearchHit]
    retrieval_status: Literal["ok", "partial", "degraded", "failed"]
    missing_sources: list[str] = Field(default_factory=list)


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4_000)
    limit: int = Field(default=8, ge=1, le=12)


class AskResult(BaseModel):
    answer: str
    points: list[str] = Field(default_factory=list)
    pattern_name: str | None = None
    mermaid: str | None = None
    confidence: float = 0.0
    source: Literal["knowledge", "model", "web"] = "knowledge"
    grounded: bool = False
    citations: list[SearchHit] = Field(default_factory=list)
    retrieval_status: Literal["ok", "partial", "degraded", "failed"] = "ok"
    ai_assist: dict = Field(default_factory=lambda: {"status": "skipped"})
