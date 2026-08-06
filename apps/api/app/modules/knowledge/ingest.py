"""Knowledge document ingestion (chunking + embedding)."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.ai.config import resolve_effective_ai_config
from app.ai.gateway import EmbeddingDisabledError, build_gateway
from app.db.models import EMBEDDING_VECTOR_DIM, KnowledgeChunkRow, KnowledgeDocumentRow
from app.modules.knowledge.chunking import chunk_text, content_hash
from app.modules.knowledge.schemas import DocumentCreate, DocumentOut
from app.modules.settings import service as settings_service

logger = logging.getLogger(__name__)


def _doc_out(row: KnowledgeDocumentRow) -> DocumentOut:
    return DocumentOut(
        id=str(row.id),
        title=row.title,
        source_class=row.source_class,
        chunk_count=row.chunk_count,
        status=row.status,
        content_hash=row.content_hash,
        embedding_model=row.embedding_model,
    )


def list_documents(
    db: Session, *, include_seed: bool = False
) -> list[DocumentOut]:
    q = db.query(KnowledgeDocumentRow)
    if not include_seed:
        q = q.filter(KnowledgeDocumentRow.source_class != "seed")
    rows = q.order_by(KnowledgeDocumentRow.created_at.desc()).all()
    return [_doc_out(r) for r in rows]


def _vec_for_storage(emb: list[float] | None) -> list[float] | None:
    if emb is None:
        return None
    if len(emb) != EMBEDDING_VECTOR_DIM:
        return None
    return [float(x) for x in emb]


def ingest_document(db: Session, payload: DocumentCreate) -> DocumentOut:
    chunks = chunk_text(payload.content)
    if not chunks:
        chunks = chunk_text(payload.content.strip() or payload.title)

    cfg = resolve_effective_ai_config(overrides=settings_service.get_overrides(db))
    gateway = build_gateway(cfg)

    embeddings: list[list[float]] | None = None
    status = "keyword_only"
    emb_model: str | None = None
    if cfg.embedding_provider != "none":
        try:
            embeddings = gateway.embed([c.text for c in chunks])
            status = "embedded"
            emb_model = cfg.embedding_model
        except EmbeddingDisabledError:
            status = "keyword_only"
            embeddings = None
        except Exception:
            logger.warning(
                "embedding failed during ingest; falling back to keyword_only",
                exc_info=True,
            )
            status = "keyword_only"
            embeddings = None

    doc = KnowledgeDocumentRow(
        id=uuid.uuid4(),
        title=payload.title.strip(),
        source_class=payload.source_class,
        source_key=payload.source_key,
        content=payload.content,
        content_hash=content_hash(payload.content),
        status=status,
        chunk_count=len(chunks),
        embedding_model=emb_model,
    )
    db.add(doc)
    db.flush()

    for i, ch in enumerate(chunks):
        emb = embeddings[i] if embeddings is not None else None
        db.add(
            KnowledgeChunkRow(
                id=uuid.uuid4(),
                document_id=doc.id,
                chunk_index=ch.index,
                heading=ch.heading,
                text=ch.text,
                embedding=emb,
                embedding_vec=_vec_for_storage(emb),
            )
        )
    db.commit()
    db.refresh(doc)
    return _doc_out(doc)
