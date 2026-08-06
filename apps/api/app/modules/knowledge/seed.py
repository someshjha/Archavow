"""Seed corpus ingestion (Markdown files bundled with the app)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import KnowledgeChunkRow, KnowledgeDocumentRow
from app.modules.knowledge.chunking import content_hash
from app.modules.knowledge.ingest import ingest_document
from app.modules.knowledge.schemas import DocumentCreate, DocumentOut


def _seed_dir() -> Path:
    """Resolve seed Markdown directory across local, tests, and Docker layouts."""
    here = Path(__file__).resolve()
    candidates: list[Path] = []
    # Walk up looking for knowledge/seed
    for parent in here.parents:
        candidates.append(parent / "knowledge" / "seed")
    candidates.extend(
        [
            Path.cwd() / "knowledge" / "seed",
            Path("/app/knowledge/seed"),
        ]
    )
    for p in candidates:
        if p.is_dir():
            return p
    return Path("/app/knowledge/seed")


def _seed_title(path: Path, content: str) -> str:
    for line in content.splitlines():
        s = line.strip()
        if s.startswith("# "):
            title = s[2:].strip()
            if title:
                return title[:256]
    # mf-architecture → Architecture
    stem = path.stem
    for prefix in ("mf-", "sd-", "industry-"):
        if stem.startswith(prefix):
            stem = stem[len(prefix) :]
            break
    return stem.replace("-", " ").strip().title()[:256] or path.stem


def seed_documents(db: Session) -> list[DocumentOut]:
    """Idempotently ingest Markdown seeds by stable source_key (relative path)."""
    seed_dir = _seed_dir()
    created: list[DocumentOut] = []
    if not seed_dir.is_dir():
        return created
    paths = sorted(
        p
        for p in seed_dir.rglob("*.md")
        if p.name.lower() not in {"readme.md", "license.md"}
    )
    seen_keys: set[str] = set()
    for path in paths:
        key = path.relative_to(seed_dir).as_posix()
        seen_keys.add(key)
        content = path.read_text(encoding="utf-8")
        digest = content_hash(content)
        exists = (
            db.query(KnowledgeDocumentRow)
            .filter(
                KnowledgeDocumentRow.source_class == "seed",
                KnowledgeDocumentRow.source_key == key,
            )
            .first()
        )
        if exists is not None and exists.content_hash == digest:
            continue
        if exists is not None:
            db.query(KnowledgeChunkRow).filter(
                KnowledgeChunkRow.document_id == exists.id
            ).delete()
            db.delete(exists)
            db.flush()
        created.append(
            ingest_document(
                db,
                DocumentCreate(
                    title=_seed_title(path, content),
                    content=content,
                    source_class="seed",
                    source_key=key,
                ),
            )
        )

    # Remove seed docs deleted from disk, plus legacy hash-only rows (no source_key)
    stale = (
        db.query(KnowledgeDocumentRow)
        .filter(KnowledgeDocumentRow.source_class == "seed")
        .all()
    )
    removed = False
    for row in stale:
        if row.source_key is None or row.source_key not in seen_keys:
            db.query(KnowledgeChunkRow).filter(
                KnowledgeChunkRow.document_id == row.id
            ).delete()
            db.delete(row)
            removed = True
    if removed:
        db.commit()
    return created


def ensure_seeded(db: Session) -> dict:
    """Ensure seed corpus is present and pick up new/changed/removed seed files."""
    before = (
        db.query(KnowledgeDocumentRow)
        .filter(KnowledgeDocumentRow.source_class == "seed")
        .count()
    )
    created = seed_documents(db)
    after = (
        db.query(KnowledgeDocumentRow)
        .filter(KnowledgeDocumentRow.source_class == "seed")
        .count()
    )
    return {
        "had_seed_docs": before,
        "created": len(created),
        "seed_docs_after": after,
    }
