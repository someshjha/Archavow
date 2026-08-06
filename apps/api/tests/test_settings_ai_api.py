"""Settings AI HTTP API — requires Postgres."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_ai_settings_shape(client: TestClient) -> None:
    res = client.get("/api/v1/settings/ai")
    assert res.status_code == 200, res.text
    data = res.json()
    body = data.get("data", data)
    assert body["chat_provider"] in {"ollama", "openai"}
    assert body["embedding_provider"] in {"ollama", "openai", "none"}
    assert body["embedding_dimensions"] == 768
    assert "openai_api_key_configured" in body
    assert "openai_api_key" not in body
    assert "OPENAI_API_KEY" not in str(body)


def test_patch_ai_settings_chat_and_embeddings(client: TestClient) -> None:
    res = client.patch(
        "/api/v1/settings/ai",
        json={
            "chat_provider": "openai",
            "chat_model": "gpt-4o-mini",
            "embedding_provider": "ollama",
            "embedding_model": "nomic-embed-text",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json().get("data", res.json())
    assert body["chat_provider"] == "openai"
    assert body["chat_model"] == "gpt-4o-mini"
    assert body["embedding_provider"] == "ollama"

    again = client.get("/api/v1/settings/ai")
    persisted = again.json().get("data", again.json())
    assert persisted["chat_provider"] == "openai"
    assert persisted["embedding_provider"] == "ollama"


def test_patch_rejects_api_key_in_body(client: TestClient) -> None:
    res = client.patch(
        "/api/v1/settings/ai",
        json={"openai_api_key": "sk-should-be-ignored"},
    )
    assert res.status_code in {200, 422}
    if res.status_code == 200:
        body = res.json().get("data", res.json())
        assert "openai_api_key" not in body
        assert body.get("openai_api_key_configured") is False


def test_probe_chat_unreachable(client: TestClient) -> None:
    res = client.post("/api/v1/settings/ai/probe/chat")
    assert res.status_code == 200, res.text
    body = res.json().get("data", res.json())
    assert "ok" in body
    assert body["ok"] is False
    assert body["reachable"] is False
    assert body["provider"] in {"ollama", "openai"}


def test_probe_embeddings_when_none(client: TestClient) -> None:
    client.patch("/api/v1/settings/ai", json={"embedding_provider": "none"})
    res = client.post("/api/v1/settings/ai/probe/embeddings")
    assert res.status_code == 200, res.text
    body = res.json().get("data", res.json())
    assert body["provider"] == "none"
    assert body["ok"] is True
