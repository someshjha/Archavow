"""Hybrid keyword + semantic retrieval over the knowledge base."""

from __future__ import annotations

import re
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.ai.config import resolve_effective_ai_config
from app.ai.gateway import build_gateway
from app.db.models import EMBEDDING_VECTOR_DIM, KnowledgeChunkRow, KnowledgeDocumentRow
from app.modules.knowledge.schemas import SearchHit, SearchRequest, SearchResult
from app.modules.settings import service as settings_service

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "then",
        "else",
        "when",
        "at",
        "by",
        "for",
        "with",
        "about",
        "against",
        "between",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "to",
        "from",
        "up",
        "down",
        "in",
        "out",
        "on",
        "off",
        "over",
        "under",
        "again",
        "further",
        "once",
        "here",
        "there",
        "all",
        "any",
        "both",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "can",
        "will",
        "just",
        "don",
        "should",
        "now",
        "what",
        "which",
        "who",
        "whom",
        "this",
        "that",
        "these",
        "those",
        "am",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "having",
        "do",
        "does",
        "did",
        "doing",
        "how",
        "why",
        "where",
        "when",
        "required",
        "require",
        "using",
        "use",
        "used",
        "via",
        "per",
        "also",
        "within",
        "without",
        "into",
        "please",
        "need",
        "needs",
        "must",
    }
)


def _tokenize(text: str) -> set[str]:
    return {
        t
        for t in re.findall(r"[a-z0-9]{3,}", text.lower())
        if t not in _STOPWORDS
    }


def _keyword_score(query: str, text: str) -> float:
    q = _tokenize(query)
    if not q:
        return 0.0
    doc = _tokenize(text)
    if not doc:
        return 0.0
    overlap = len(q & doc)
    return overlap / len(q)


def _phrase_boost(query: str, text: str) -> float:
    """Boost consecutive meaningful token matches (exact phrase fragments)."""
    q_tokens = [
        t
        for t in re.findall(r"[a-z0-9]{3,}", query.lower())
        if t not in _STOPWORDS
    ]
    if len(q_tokens) < 2:
        return 0.0
    hay = f" {text.lower()} "
    boost = 0.0
    # Prefer longer windows first
    for n in (3, 2):
        if len(q_tokens) < n:
            continue
        for i in range(0, len(q_tokens) - n + 1):
            phrase = " ".join(q_tokens[i : i + n])
            if f" {phrase} " in hay or phrase in hay:
                boost = max(boost, 0.18 if n >= 3 else 0.12)
    return boost


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return float(dot / (na * nb))


def search(db: Session, payload: SearchRequest) -> SearchResult:
    cfg = resolve_effective_ai_config(overrides=settings_service.get_overrides(db))
    tokens = sorted(_tokenize(payload.query), key=len, reverse=True)[:8]
    base = db.query(KnowledgeChunkRow, KnowledgeDocumentRow).join(
        KnowledgeDocumentRow, KnowledgeChunkRow.document_id == KnowledgeDocumentRow.id
    )

    # Keyword candidates (bounded) — stopword-filtered tokens only
    keyword_rows: list[tuple[Any, Any]] = []
    if tokens:
        from sqlalchemy import or_

        clauses = []
        for tok in tokens[:5]:
            like = f"%{tok}%"
            clauses.append(KnowledgeChunkRow.text.ilike(like))
            clauses.append(KnowledgeDocumentRow.title.ilike(like))
        keyword_rows = base.filter(or_(*clauses)).limit(200).all()

    query_vec: list[float] | None = None
    retrieval_status: Literal["ok", "partial", "degraded", "failed"] = "ok"
    missing: list[str] = []
    stale_embeddings = False

    if cfg.embedding_provider == "none":
        retrieval_status = "degraded"
        missing.append("embeddings_disabled")
    else:
        try:
            gateway = build_gateway(cfg)
            query_vec = gateway.embed([payload.query])[0]
        except Exception:
            retrieval_status = "partial"
            missing.append("query_embed_failed")

    # Semantic candidates: true nearest neighbours via pgvector when dims match
    embed_rows: list[tuple[Any, Any]] = []
    if query_vec is not None and len(query_vec) == EMBEDDING_VECTOR_DIM:
        try:
            embed_rows = (
                base.filter(KnowledgeChunkRow.embedding_vec.isnot(None))
                .order_by(KnowledgeChunkRow.embedding_vec.cosine_distance(query_vec))
                .limit(50)
                .all()
            )
        except Exception:
            missing.append("pgvector_nn_failed")
            retrieval_status = "partial" if retrieval_status == "ok" else retrieval_status
            # Fallback: score JSONB embeddings from a broader recent pool
            embed_rows = (
                base.filter(KnowledgeChunkRow.embedding.isnot(None))
                .order_by(KnowledgeChunkRow.created_at.desc())
                .limit(400)
                .all()
            )
    elif query_vec is not None:
        missing.append("embedding_dim_mismatch")
        retrieval_status = "partial" if retrieval_status == "ok" else retrieval_status
        embed_rows = (
            base.filter(KnowledgeChunkRow.embedding.isnot(None))
            .order_by(KnowledgeChunkRow.created_at.desc())
            .limit(400)
            .all()
        )

    merged: dict[Any, tuple[Any, Any]] = {}
    for chunk, doc in keyword_rows + embed_rows:
        merged[chunk.id] = (chunk, doc)
    rows = list(merged.values())

    if not rows:
        # Last resort bounded sample so empty keyword+embed pools still searchable
        rows = base.order_by(KnowledgeChunkRow.created_at.desc()).limit(200).all()

    if not rows:
        return SearchResult(
            hits=[],
            retrieval_status="degraded" if cfg.embedding_provider == "none" else "ok",
            missing_sources=missing,
        )

    scored: list[tuple[float, Any, Any]] = []
    for chunk, doc in rows:
        blob = f"{doc.title} {chunk.heading or ''} {chunk.text}"
        kw = _keyword_score(payload.query, blob)
        title_hit = _keyword_score(payload.query, doc.title)
        phrase = _phrase_boost(payload.query, blob)
        sem = 0.0
        if query_vec is not None and isinstance(chunk.embedding, list):
            emb = [float(x) for x in chunk.embedding]
            model_ok = (doc.embedding_model or "") == (cfg.embedding_model or "")
            dim_ok = len(emb) == len(query_vec)
            if model_ok and dim_ok:
                sem = _cosine(query_vec, emb)
            elif emb:
                stale_embeddings = True
        score = kw * 0.55 + sem * 0.45 if query_vec is not None else kw
        score += min(0.2, title_hit * 0.25)
        score += phrase
        # Prefer org/project standards slightly over generic seed strategy text
        if doc.source_class in {"org", "project"} and (kw > 0 or phrase > 0):
            score += 0.08
        if score > 0:
            scored.append((score, chunk, doc))

    if stale_embeddings and retrieval_status == "ok":
        retrieval_status = "partial"
        missing.append("stale_embeddings")

    scored.sort(key=lambda t: t[0], reverse=True)
    hits: list[SearchHit] = []
    for score, chunk, doc in scored[: payload.limit]:
        cite = f"{doc.title}" + (f" › {chunk.heading}" if chunk.heading else "")
        hits.append(
            SearchHit(
                document_id=str(doc.id),
                chunk_id=str(chunk.id),
                title=doc.title,
                source_class=doc.source_class,
                text=chunk.text,
                score=round(float(score), 4),
                citation=cite,
            )
        )

    if not hits and rows:
        return SearchResult(hits=[], retrieval_status=retrieval_status, missing_sources=missing)

    return SearchResult(hits=hits, retrieval_status=retrieval_status, missing_sources=missing)
