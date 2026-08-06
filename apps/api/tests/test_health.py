"""Health — requires Postgres for ok status."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_ok_shape(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] in {"ok", "degraded"}
    assert "postgres" in body
    assert "ai" in body
    assert "chat_provider" in body["ai"]
    assert "embedding_provider" in body["ai"]
    assert body["postgres"]["ok"] is True
    assert body["status"] == "ok"
