"""Postgres-only integration: Alembic, pgvector NN, row locking."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import KnowledgeChunkRow, KnowledgeDocumentRow
from app.db.session import get_engine
from tests.db_helpers import require_postgres


def test_alembic_head_and_vector_extension(client: TestClient) -> None:
    require_postgres()
    engine = get_engine()
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert version, "expected alembic_version after upgrade"
        ext = conn.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one()
        assert ext == "vector"
        # Fixed 768-dim column from migration 0017
        col = conn.execute(
            text(
                """
                SELECT format_type(a.atttypid, a.atttypmod)
                FROM pg_attribute a
                JOIN pg_class c ON a.attrelid = c.oid
                JOIN pg_namespace n ON c.relnamespace = n.oid
                WHERE n.nspname = 'public'
                  AND c.relname = 'knowledge_chunks'
                  AND a.attname = 'embedding_vec'
                  AND NOT a.attisdropped
                """
            )
        ).scalar_one()
        assert "vector" in col


def test_pgvector_cosine_nearest_neighbor(client: TestClient, db: Session) -> None:
    require_postgres()
    dim = 768
    near = [0.0] * dim
    near[0] = 1.0
    far = [0.0] * dim
    far[1] = 1.0

    doc = KnowledgeDocumentRow(
        id=uuid.uuid4(),
        title="pgvector-nn.md",
        source_class="org",
        content="# pgvector\n\nnear and far chunks",
        content_hash="abc",
        status="embedded",
        chunk_count=2,
        embedding_model="test-embed",
    )
    db.add(doc)
    db.flush()
    near_id = uuid.uuid4()
    far_id = uuid.uuid4()
    db.add_all(
        [
            KnowledgeChunkRow(
                id=near_id,
                document_id=doc.id,
                chunk_index=0,
                text="near vector chunk about OAuth",
                embedding=near,
                embedding_vec=near,
            ),
            KnowledgeChunkRow(
                id=far_id,
                document_id=doc.id,
                chunk_index=1,
                text="far vector chunk about baking",
                embedding=far,
                embedding_vec=far,
            ),
        ]
    )
    db.commit()

    # Use the cosine distance operator directly — EmbeddingVector is a
    # with_variant wrapper, so the ORM comparator may not expose helpers.
    vec_literal = "[" + ",".join(f"{x:.6f}" for x in near) + "]"
    ordered = db.execute(
        text(
            """
            SELECT id FROM knowledge_chunks
            WHERE document_id = CAST(:doc AS uuid)
            ORDER BY embedding_vec <=> CAST(:vec AS vector)
            """
        ),
        {"doc": str(doc.id), "vec": vec_literal},
    ).scalars().all()
    assert [uuid.UUID(str(x)) for x in ordered] == [near_id, far_id]


def test_for_update_locks_on_postgres(client: TestClient, db: Session) -> None:
    """SQLite accepts FOR UPDATE loosely; Postgres must honour row locks."""
    require_postgres()
    created = client.post(
        "/api/v1/projects",
        json={"name": "Lock Me", "stack_tags": ["postgres"]},
    )
    assert created.status_code == 201, created.text
    pid = created.json()["data"]["id"]

    from app.db.models import ProjectRow

    row = (
        db.query(ProjectRow)
        .filter(ProjectRow.id == uuid.UUID(pid))
        .with_for_update()
        .one()
    )
    assert row.name == "Lock Me"
    db.commit()
