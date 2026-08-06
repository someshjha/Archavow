"""Dialect-portable column types (Postgres in prod, SQLite in unit tests)."""

from __future__ import annotations

from sqlalchemy import JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector

# JSONB on Postgres; JSON on SQLite (and other dialects).
JSONType = JSON().with_variant(JSONB(), "postgresql")

# Native UUID on Postgres; portable Uuid elsewhere (SQLite stores as CHAR).
UUIDType = Uuid(as_uuid=True).with_variant(UUID(as_uuid=True), "postgresql")


def EmbeddingVector(dim: int):
    """pgvector on Postgres; JSON float list on SQLite (NN falls back in service)."""
    return JSON().with_variant(Vector(dim), "postgresql")
