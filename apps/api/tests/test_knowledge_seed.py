"""Knowledge seed library ingest + hidden listing + ask answers."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_seed_library_is_idempotent(client: TestClient) -> None:
    first = client.post("/api/v1/knowledge/seed")
    assert first.status_code == 201, first.text
    body = first.json()["data"]
    assert body["count"] >= 20, body["count"]

    second = client.post("/api/v1/knowledge/seed")
    assert second.status_code == 201
    assert second.json()["data"]["count"] == 0


def test_seed_documents_hidden_from_default_list(client: TestClient) -> None:
    client.post("/api/v1/knowledge/seed")
    listed = client.get("/api/v1/knowledge/documents").json()["data"]
    assert all(d["source_class"] != "seed" for d in listed)

    with_seed = client.get("/api/v1/knowledge/documents?include_seed=true").json()["data"]
    assert any(d["source_class"] == "seed" for d in with_seed)


def test_documents_list_does_not_auto_seed(client: TestClient) -> None:
    listed = client.get("/api/v1/knowledge/documents")
    assert listed.status_code == 200, listed.text
    seeded = client.get("/api/v1/knowledge/documents?include_seed=true").json()["data"]
    assert seeded == []

    client.post("/api/v1/knowledge/seed")
    after = client.get("/api/v1/knowledge/documents?include_seed=true").json()["data"]
    assert len([d for d in after if d["source_class"] == "seed"]) >= 20


def test_ask_returns_precise_answer_from_seeds(client: TestClient) -> None:
    client.post("/api/v1/knowledge/seed")
    res = client.post(
        "/api/v1/knowledge/ask",
        json={"query": "Kafka dead letter queue DLQ retention", "limit": 6},
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["answer"]
    assert len(data["answer"]) < 2000
    assert data["source"] in {"knowledge", "model", "web"}
    assert "seed" not in data["answer"].lower()
    assert "corpus" not in data["answer"].lower()
    # Knowledge path may cite remapped industry hits; model/web must not
    if data["source"] == "knowledge":
        assert data["citations"]
        assert data.get("grounded") is True
        assert all(c["source_class"] != "seed" for c in data["citations"])
    else:
        assert data["citations"] == []
        assert data.get("grounded") is False


def test_ask_model_or_web_fallback_has_empty_citations(
    client: TestClient, monkeypatch
) -> None:
    """Rejected KB hits must never become provenance for model/web answers."""
    from app.ai.assist import AiAssistStatus
    from app.ai.knowledge_assist import KnowledgeAnswer
    from app.ai import knowledge_assist as assist_mod

    client.post("/api/v1/knowledge/seed")

    def _weak_kb(gateway, query, hits):  # noqa: ANN001
        return KnowledgeAnswer(
            answer="weak",
            points=[],
            confidence=0.1,
            best_candidate_score=0.1,
            source="knowledge",
            status=AiAssistStatus(status="ok", detail="weak"),
        )

    def _online(gateway, query):  # noqa: ANN001
        return KnowledgeAnswer(
            answer="CQRS separates command and query models.",
            points=["Write side owns commands", "Read side serves queries"],
            pattern_name="CQRS",
            confidence=0.7,
            source="model",
            status=AiAssistStatus(status="ok", detail="model_fallback"),
        )

    monkeypatch.setattr(assist_mod, "compose_scored_knowledge_answer", _weak_kb)
    monkeypatch.setattr(assist_mod, "answer_online_or_model", _online)

    res = client.post(
        "/api/v1/knowledge/ask",
        json={"query": "What is CQRS?", "limit": 6},
    )
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["source"] == "model"
    assert data["citations"] == []
    assert data.get("grounded") is False
    assert "CQRS" in data["answer"]


def test_package_generate_captures_project_decisions(client: TestClient) -> None:
    created = client.post(
        "/api/v1/projects",
        json={
            "name": "Capture Decisions Platform",
            "business_objective": "Event payments",
            "problem_statement": "Batch misses SLAs",
            "preferred_cloud": "Azure",
            "scale_availability": "5k events/sec · 99.9%",
            "tech_constraints": "Spring Boot, Kafka, AKS",
            "stack_tags": ["azure", "kafka"],
        },
    )
    assert created.status_code == 201, created.text
    pid = created.json()["data"]["id"]
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    pkg = client.post(f"/api/v1/projects/{pid}/package/generate")
    assert pkg.status_code == 200, pkg.text

    listed = client.get("/api/v1/knowledge/documents").json()["data"]
    project_docs = [d for d in listed if d["source_class"] == "project"]
    assert project_docs, listed
    assert any("Capture Decisions" in d["title"] for d in project_docs)

    # Regenerating replaces the prior capture (same title)
    client.post(f"/api/v1/projects/{pid}/package/generate")
    again = [
        d
        for d in client.get("/api/v1/knowledge/documents").json()["data"]
        if d["source_class"] == "project" and "Capture Decisions" in d["title"]
    ]
    assert len(again) == 1


def test_me_auth_stub(client: TestClient) -> None:
    res = client.get("/api/v1/me")
    assert res.status_code == 200
    assert res.json()["data"]["auth"] == "stub"
