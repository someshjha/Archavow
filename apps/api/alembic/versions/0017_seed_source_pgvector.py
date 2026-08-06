"""Seed source_key + pgvector embedding column

Revision ID: 0017_seed_source_pgvector
Revises: 0016_concurrency_uniques
Create Date: 2026-07-31
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017_seed_source_pgvector"
down_revision: Union[str, None] = "0016_concurrency_uniques"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Matches default OPENAI_EMBEDDING_DIMENSIONS / Ollama nomic-embed-text usage.
_VECTOR_DIM = 768


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "knowledge_documents",
        sa.Column("source_key", sa.String(length=512), nullable=True),
    )
    op.create_index(
        "ux_knowledge_documents_source_key",
        "knowledge_documents",
        ["source_key"],
        unique=True,
        postgresql_where=sa.text("source_key IS NOT NULL"),
    )
    op.execute(
        f"ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS embedding_vec vector({_VECTOR_DIM})"
    )
    # Best-effort backfill when JSONB embeddings already match the configured dim.
    op.execute(
        f"""
        UPDATE knowledge_chunks AS kc
        SET embedding_vec = sub.vec
        FROM (
            SELECT id,
                   (
                     SELECT array_agg(value::float ORDER BY ordinality)::vector({_VECTOR_DIM})
                     FROM jsonb_array_elements_text(embedding)
                          WITH ORDINALITY AS t(value, ordinality)
                   ) AS vec
            FROM knowledge_chunks
            WHERE embedding IS NOT NULL
              AND jsonb_typeof(embedding) = 'array'
              AND jsonb_array_length(embedding) = {_VECTOR_DIM}
        ) AS sub
        WHERE kc.id = sub.id
          AND kc.embedding_vec IS NULL
        """
    )
    # No IVFFlat/HNSW yet — corpora are small; cosine ORDER BY remains correct without an index.


def downgrade() -> None:
    op.execute("ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS embedding_vec")
    op.drop_index(
        "ux_knowledge_documents_source_key",
        table_name="knowledge_documents",
    )
    op.drop_column("knowledge_documents", "source_key")
