"""AI-generated architecture options (with deterministic fallback)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.ai.gateway import AIGateway
from tests.fakes import FakeChatProvider, FakeEmbeddingProvider


def _fake_gateway(json_response: dict, *, raise_on_json: bool = False):
    chat = FakeChatProvider(json_response=json_response)

    if raise_on_json:

        def boom(*_a, **_k):
            raise ConnectionError("chat down")

        chat.complete_json = boom  # type: ignore[method-assign]

    def build(cfg):
        return AIGateway(cfg, chat, FakeEmbeddingProvider())

    return build, chat


def _ready_project(client: TestClient) -> str:
    res = client.post(
        "/api/v1/projects",
        json={
            "name": "AKS Event Platform",
            "business_objective": "Payment events on Azure",
            "problem_statement": "Batch misses SLAs",
            "preferred_cloud": "Azure",
            "scale_availability": "5k events/sec peak · 99.9%",
            "tech_constraints": "Spring Boot, Kafka, AKS",
            "stack_tags": ["azure", "kafka", "spring-boot"],
        },
    )
    assert res.status_code == 201
    pid = res.json()["data"]["id"]
    analyzed = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    rto = next((q for q in analyzed["questions"] if q["code"] == "rto_rpo"), None)
    if rto:
        client.post(
            f"/api/v1/projects/{pid}/interview/answer",
            json={"question_id": rto["id"], "answer": "RTO 15 min · RPO 1 min"},
        )
    return pid


def test_options_from_ai_when_chat_ok(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    design = {
        "approach": "Event-driven payments spine with Postgres SoR.",
        "assumptions": ["Team can run AKS day-two", "Kafka skills exist"],
        "constraints": ["Stay on Azure", "Postgres as SoR"],
        "key_decisions": ["Service boundaries vs modular monolith"],
    }
    build, chat = _fake_gateway(
        {
            "options": [
                {
                    "key": "ai_recommended",
                    "title": "Event Hub + AKS payments spine",
                    "summary": "Kafka-protocol Event Hubs with Spring services on AKS.",
                    "pros": ["Native Azure ops", "Strong streaming fit", "Clear SoR with Postgres"],
                    "cons": ["Broker cost", "Needs Kafka skills"],
                    "fit_score": 88,
                    "cost_band": "$$$",
                    "ops_band": "high",
                    "recommended": True,
                    "stack": ["aks", "event-hubs", "postgres", "spring-boot"],
                    **design,
                },
                {
                    "key": "ai_lower_cost",
                    "title": "Container Apps + Service Bus",
                    "summary": "Simpler PaaS path for moderate scale.",
                    "pros": ["Lower ops", "Faster MVP"],
                    "cons": ["Weaker extreme throughput", "Less Kafka tooling"],
                    "fit_score": 72,
                    "cost_band": "$$",
                    "ops_band": "medium",
                    "recommended": False,
                    "stack": ["container-apps", "service-bus", "postgres"],
                    **design,
                },
                {
                    "key": "ai_resilience",
                    "title": "Active-active multi-region Kafka",
                    "summary": "MirrorMaker / geo for aggressive RPO.",
                    "pros": ["Near-zero RPO", "Region isolation"],
                    "cons": ["Highest cost", "Complex dual-write"],
                    "fit_score": 81,
                    "cost_band": "$$$$",
                    "ops_band": "very high",
                    "recommended": False,
                    "stack": ["aks", "kafka", "mirrormaker", "postgres"],
                    **design,
                },
            ]
        }
    )
    monkeypatch.setattr("app.modules.options.service.build_gateway", build)
    # interview also uses gateway — don't fail analyze
    monkeypatch.setattr(
        "app.modules.requirements.service.build_gateway",
        _fake_gateway(
            {
                "intro": "hi",
                "rewrites": {},
                "followups": [],
                "reply": "ok",
                "executive_summary": "x",
                "options": [],
            }
        )[0],
    )

    pid = _ready_project(client)
    res = client.post(f"/api/v1/projects/{pid}/options/generate")
    assert res.status_code == 200, res.text
    body = res.json()["data"]
    assert body["ai_assist"]["status"] == "ok"
    assert chat.complete_json_calls >= 1
    titles = {o["title"] for o in body["options"]}
    assert "Event Hub + AKS payments spine" in titles
    assert sum(1 for o in body["options"] if o["recommended"]) == 1
    assert all(len(o["pros"]) >= 2 and len(o["cons"]) >= 2 for o in body["options"])
    rec = next(o for o in body["options"] if o["recommended"])
    assert rec["design"]["approach"]
    assert rec["design"]["assumptions"]
    assert rec["design"]["constraints"]
    assert rec["design"]["key_decisions"]


def test_options_fallback_when_chat_fails(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    build, _ = _fake_gateway({}, raise_on_json=True)
    monkeypatch.setattr("app.modules.options.service.build_gateway", build)
    monkeypatch.setattr(
        "app.modules.requirements.service.build_gateway",
        _fake_gateway({"intro": "hi", "rewrites": {}, "followups": [], "reply": "ok"}, raise_on_json=True)[0],
    )

    pid = _ready_project(client)
    res = client.post(f"/api/v1/projects/{pid}/options/generate")
    assert res.status_code == 200, res.text
    body = res.json()["data"]
    assert body["ai_assist"]["status"] in {"failed", "skipped"}
    assert len(body["options"]) == 3
    assert any("Kafka" in o["title"] or "AKS" in o["title"] or "services" in o["title"].lower() for o in body["options"])
    assert all(o.get("design", {}).get("approach") for o in body["options"])


def test_options_unexpected_bug_does_not_become_templates(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Programming defects must not be polished into successful template options."""

    def boom(*_a, **_k):
        raise AttributeError("simulated assist bug")

    monkeypatch.setattr(
        "app.modules.options.options_ops.generate_architecture_options", boom
    )
    monkeypatch.setattr(
        "app.modules.requirements.service.build_gateway",
        _fake_gateway({"intro": "hi", "rewrites": {}, "followups": [], "reply": "ok"})[0],
    )
    pid = _ready_project(client)
    with pytest.raises(AttributeError, match="simulated assist bug"):
        client.post(f"/api/v1/projects/{pid}/options/generate")
