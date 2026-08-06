"""DB helpers for tests — default is in-memory SQLite (no external Postgres)."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

# Unit tests default to SQLite in-memory. Opt into real Postgres with:
#   ARCHAVOW_TEST_DB=postgres pytest
# or by setting DATABASE_URL to a postgresql:// URL before pytest.
SQLITE_TEST_URL = "sqlite+pysqlite:///:memory:"
POSTGRES_TEST_URL = "postgresql+psycopg://archavow:archavow@127.0.0.1:5433/archavow"


def _resolve_test_database_url() -> str:
    explicit = os.environ.get("DATABASE_URL", "").strip()
    mode = os.environ.get("ARCHAVOW_TEST_DB", "").strip().lower()
    if mode in {"postgres", "postgresql", "pg"}:
        return explicit or POSTGRES_TEST_URL
    if explicit.startswith("postgresql"):
        return explicit
    if explicit.startswith("sqlite"):
        return explicit
    return SQLITE_TEST_URL


DATABASE_URL = _resolve_test_database_url()


def using_postgres() -> bool:
    return DATABASE_URL.startswith("postgresql")


def create_test_engine(url: str | None = None):
    url = url or DATABASE_URL
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(url, pool_pre_ping=True)


def postgres_reachable() -> bool:
    if not using_postgres():
        return False
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def require_postgres() -> None:
    """Skip when a test explicitly needs real Postgres (pgvector NN, etc.)."""
    if not using_postgres():
        pytest.skip("Postgres-only test (set ARCHAVOW_TEST_DB=postgres)")
    if not postgres_reachable():
        pytest.skip(
            f"Postgres not reachable at {DATABASE_URL}. "
            "Start with: docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres"
        )
