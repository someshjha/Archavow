"""SQLAlchemy session + FastAPI dependency."""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

_DEFAULT_URL = "postgresql+psycopg://archavow:archavow@127.0.0.1:5433/archavow"

_engine = None
_SessionLocal = None


def database_url() -> str:
    return os.environ.get("DATABASE_URL", _DEFAULT_URL)


def _engine_kwargs(url: str) -> dict:
    """SQLite in-memory needs StaticPool so all connections share one DB."""
    if url.startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    return {"pool_pre_ping": True}


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = database_url()
        _engine = create_engine(url, **_engine_kwargs(url))
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def get_session_factory():
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def reset_engine() -> None:
    """Clear cached engine (tests that change DATABASE_URL)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_db() -> Generator[Session, None, None]:
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
