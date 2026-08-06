"""Projects + AI settings persist across SQLAlchemy sessions (SQLite or Postgres)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db.session import get_engine


def test_project_survives_new_session(client: TestClient) -> None:
    created = client.post(
        "/api/v1/projects",
        json={"name": "Persist Me", "stack_tags": ["kafka"]},
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["data"]["id"]

    from app.db.session import get_db
    from app.main import app as fastapi_app

    # Same engine as the client fixture (StaticPool memory or shared Postgres).
    engine = get_engine()
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as client2:
        got = client2.get(f"/api/v1/projects/{project_id}")
        assert got.status_code == 200, got.text
        assert got.json()["data"]["name"] == "Persist Me"
        assert "kafka" in got.json()["data"]["stack_tags"]


def test_ai_settings_persist(client: TestClient) -> None:
    patched = client.patch(
        "/api/v1/settings/ai",
        json={"chat_provider": "openai", "embedding_provider": "ollama"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["chat_provider"] == "openai"

    again = client.get("/api/v1/settings/ai")
    assert again.json()["data"]["chat_provider"] == "openai"
    assert again.json()["data"]["embedding_provider"] == "ollama"
    assert "openai_api_key" not in again.json()["data"]


def test_health_postgres_ok(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["postgres"]["ok"] is True
    assert body["status"] == "ok"
