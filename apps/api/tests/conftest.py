from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from tests.db_helpers import DATABASE_URL, create_test_engine, using_postgres


@pytest.fixture()
def env_ollama_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_CHAT_PROVIDER", "ollama")
    monkeypatch.setenv("AI_EMBEDDING_PROVIDER", "none")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_CHAT_MODEL", "llama3.2")
    monkeypatch.setenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    monkeypatch.setenv("OPENAI_EMBEDDING_DIMENSIONS", "768")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


_test_session_maker = None


@pytest.fixture()
def db():
    """Direct database session for low-level testing (bypasses TestClient)."""
    global _test_session_maker
    if _test_session_maker is None:
        raise RuntimeError("db fixture requires client fixture to be used first")
    session = _test_session_maker()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """HTTP client against API with in-memory SQLite (or Postgres when opted in).

    SQLite: schema via Base.metadata.create_all (fast, no external DB).
    Postgres: schema via Alembic migrations so migration drift fails tests.
    """
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    monkeypatch.setenv("AI_CHAT_PROVIDER", "ollama")
    monkeypatch.setenv("AI_EMBEDDING_PROVIDER", "none")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("AUTO_SEED_KNOWLEDGE", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ARCHAVOW_API_KEY", raising=False)
    monkeypatch.setenv("AUTO_CREATE_TABLES", "false")
    monkeypatch.setenv("AUTO_MIGRATE", "false")
    monkeypatch.setenv("ALLOW_PRIVATE_AI_URLS", "true")

    from app.db.base import Base
    from app.db.session import get_db, reset_engine
    import app.db.models  # noqa: F401 — register metadata
    from app.main import app as fastapi_app

    reset_engine()

    if using_postgres():
        from pathlib import Path

        from alembic import command
        from alembic.config import Config
        from sqlalchemy import text

        engine = create_test_engine(DATABASE_URL)
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        api_root = Path(__file__).resolve().parents[1]
        alembic_cfg = Config(str(api_root / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(api_root / "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        command.upgrade(alembic_cfg, "head")
    else:
        # Share one StaticPool memory DB with app.db.session.get_engine().
        from app.db.session import get_engine

        engine = get_engine()
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    global _test_session_maker
    _test_session_maker = TestingSession

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
    reset_engine()
    _test_session_maker = None
