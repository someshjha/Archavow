"""Chat-assisted interview follow-ups + package summary (gateway, with fallback)."""

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


def _project(client: TestClient) -> str:
    res = client.post(
        "/api/v1/projects",
        json={
            "name": "AKS Event Platform",
            "business_objective": "Real-time payment event processing for merchant settlement",
            "preferred_cloud": "Azure",
            "tech_constraints": "Spring Boot services on AKS, using Kafka for streaming",
        },
    )
    assert res.status_code == 201
    return res.json()["data"]["id"]


def test_interview_analyze_adds_ai_followups(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    build, chat = _fake_gateway(
        {
            "intro": "Let's nail NFRs for AKS Event Platform on Azure.",
            "rewrites": {
                "rto_rpo": "For payment events on AKS, what RTO/RPO do you need if the primary Azure region fails?",
            },
            "sufficient": False,
            "followup": {
                "code": "ai_tenant_isolation",
                "prompt": "How will tenant data be isolated at rest and in transit?",
                "category": "security",
            },
            "reply": "Got it — noted.",
            "executive_summary": "Event-driven AKS platform with Kafka.",
        }
    )
    monkeypatch.setattr("app.modules.requirements.service.build_gateway", build)

    pid = _project(client)
    res = client.post(f"/api/v1/projects/{pid}/interview/analyze")
    assert res.status_code == 200, res.text
    body = res.json()["data"]
    assert body["ai_assist"]["status"] == "ok"
    assert body["intro"]
    assert chat.complete_json_calls >= 1
    codes = {q["code"] for q in body["questions"]}
    assert "ai_tenant_isolation" in codes
    rto = next(q for q in body["questions"] if q["code"] == "rto_rpo")
    assert "payment" in rto["prompt"].lower() or "aks" in rto["prompt"].lower()


def test_interview_stops_asking_once_ai_reports_sufficient(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No more AI follow-ups get queued once the model says it has enough —
    this is what replaces a fixed count cap."""

    def build(cfg):  # noqa: ANN001
        from app.ai.gateway import AIGateway
        from tests.fakes import FakeChatProvider, FakeEmbeddingProvider

        payload = {
            "intro": "Hi",
            "rewrites": {},
            "sufficient": True,
            "followup": None,
            "reply": "ok",
        }
        return AIGateway(cfg, FakeChatProvider(json_response=payload), FakeEmbeddingProvider())

    monkeypatch.setattr("app.modules.requirements.service.build_gateway", build)

    pid = _project(client)
    first = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    assert [q for q in first["questions"] if q["code"].startswith("ai_")] == []

    rto = next(q for q in first["questions"] if q["code"] == "rto_rpo")
    answered = client.post(
        f"/api/v1/projects/{pid}/interview/answer",
        json={"question_id": rto["id"], "answer": "RTO 15 min · RPO 1 min"},
    )
    assert answered.status_code == 200, answered.text
    ai_after = [q for q in answered.json()["data"]["questions"] if q["code"].startswith("ai_")]
    assert ai_after == []


def test_interview_follow_ups_stop_at_safety_ceiling(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A model that never reports sufficient still stops eventually — bounded
    by the safety ceiling, not by a product-facing count."""
    from app.modules.requirements.service import MAX_AI_FOLLOWUPS_SAFETY

    call_n = {"n": 0}

    def build(cfg):  # noqa: ANN001
        from app.ai.gateway import AIGateway
        from tests.fakes import FakeChatProvider, FakeEmbeddingProvider

        call_n["n"] += 1
        payload = {
            "intro": "Hi",
            "rewrites": {},
            "sufficient": False,
            "followup": {
                "code": f"ai_never_enough_{call_n['n']}",
                "prompt": "Another question that never satisfies the model?",
                "category": "requirements",
            },
            "reply": "ok",
        }
        return AIGateway(cfg, FakeChatProvider(json_response=payload), FakeEmbeddingProvider())

    monkeypatch.setattr("app.modules.requirements.service.build_gateway", build)

    pid = _project(client)
    state = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    assert len([q for q in state["questions"] if q["code"].startswith("ai_")]) == 1

    for _ in range(MAX_AI_FOLLOWUPS_SAFETY + 5):
        state = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    ai_codes = [q["code"] for q in state["questions"] if q["code"].startswith("ai_")]
    assert len(ai_codes) == MAX_AI_FOLLOWUPS_SAFETY


def test_reopened_question_rewrite_prompt_includes_prior_attempt(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The prompt sent to the model for a previously-rejected answer must
    include that attempt, so the model can genuinely ask differently."""
    captured: dict[str, str] = {}

    def build(cfg):  # noqa: ANN001
        from app.ai.gateway import AIGateway
        from tests.fakes import FakeChatProvider, FakeEmbeddingProvider

        class CapturingChat(FakeChatProvider):
            def complete_json(self, messages, schema, *, timeout_s=None):  # noqa: ANN001
                captured["user_message"] = messages[-1].content
                return super().complete_json(messages, schema, timeout_s=timeout_s)

        payload = {"intro": "Hi", "rewrites": {}, "sufficient": False, "followup": None, "reply": "ok"}
        return AIGateway(cfg, CapturingChat(json_response=payload), FakeEmbeddingProvider())

    monkeypatch.setattr("app.modules.requirements.service.build_gateway", build)

    pid = _project(client)
    analyzed = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    peak = next(q for q in analyzed["questions"] if q["code"] == "peak_traffic")

    rejected = client.post(
        f"/api/v1/projects/{pid}/interview/answer",
        json={"question_id": peak["id"], "answer": "a decent amount honestly"},
    )
    assert rejected.status_code == 422

    client.post(f"/api/v1/projects/{pid}/interview/analyze")
    assert "a decent amount honestly" in captured["user_message"]
    assert "different angle" in captured["user_message"] or "insufficient" in captured["user_message"]


def test_interview_analyze_survives_chat_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    build, _ = _fake_gateway({"followups": []}, raise_on_json=True)
    monkeypatch.setattr("app.modules.requirements.service.build_gateway", build)

    pid = _project(client)
    res = client.post(f"/api/v1/projects/{pid}/interview/analyze")
    assert res.status_code == 200, res.text
    body = res.json()["data"]
    assert body["ai_assist"]["status"] in {"failed", "skipped"}
    # Deterministic gaps still present
    assert any(q["code"] == "rto_rpo" for q in body["questions"])


def test_interview_answer_returns_ai_reply(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    build, _ = _fake_gateway(
        {
            "intro": "Hi",
            "rewrites": {},
            "followups": [],
            "reply": "Thanks — RTO 15 / RPO 1 noted for regional failover.",
            "executive_summary": "Summary",
        }
    )
    monkeypatch.setattr("app.modules.requirements.service.build_gateway", build)

    pid = _project(client)
    analyzed = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    rto = next(q for q in analyzed["questions"] if q["code"] == "rto_rpo")
    answered = client.post(
        f"/api/v1/projects/{pid}/interview/answer",
        json={"question_id": rto["id"], "answer": "RTO 15 min · RPO 1 min"},
    )
    assert answered.status_code == 200, answered.text
    assert "RTO" in (answered.json()["data"].get("ai_reply") or "")


def test_package_includes_ai_executive_summary(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    build, chat = _fake_gateway(
        {
            "intro": "Hi",
            "rewrites": {},
            "followups": [],
            "reply": "ok",
            "executive_summary": "Event-driven AKS platform with Kafka as the backbone and Postgres as system of record.",
        }
    )
    monkeypatch.setattr("app.modules.requirements.service.build_gateway", build)
    monkeypatch.setattr("app.modules.options.service.build_gateway", build)

    pid = _project(client)
    client.post(f"/api/v1/projects/{pid}/interview/analyze")
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    pkg = client.post(f"/api/v1/projects/{pid}/package/generate")
    assert pkg.status_code == 200, pkg.text
    body = pkg.json()["data"]
    assert body["ai_assist"]["status"] == "ok"
    assert body["ai_summary"]
    assert "Kafka" in body["ai_summary"] or "event" in body["ai_summary"].lower()
    assert "## In short" in body["hld_markdown"]
    assert body["provenance"]["workflow_version"] == "package.v8"
    assert chat.complete_json_calls >= 1


def test_package_survives_chat_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    build, _ = _fake_gateway({}, raise_on_json=True)
    monkeypatch.setattr("app.modules.options.service.build_gateway", build)

    pid = _project(client)
    client.post(f"/api/v1/projects/{pid}/interview/analyze")
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    pkg = client.post(f"/api/v1/projects/{pid}/package/generate")
    assert pkg.status_code == 200, pkg.text
    body = pkg.json()["data"]
    assert body["ai_assist"]["status"] in {"failed", "skipped"}
    assert body["adrs"]  # deterministic still works
    assert "high-level design" in body["hld_markdown"].lower() or "architecture" in body["hld_markdown"].lower()


def test_package_provenance_reports_ai_hld_source(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    hld_payload = {
        "component_responsibilities": ["The ingest service validates and partitions events."],
        "technology_choices": [
            {"area": "streaming", "technology": "Apache Kafka", "why": "evidenced in constraints"}
        ],
        "integration_patterns": ["Producers publish to one topic per event type."],
        "data_ownership": ["Kafka is the durable log; Postgres holds read state."],
        "api_event_boundaries": ["Partners never see internal topic names."],
        "scaling_availability": ["Partition count scales with producer throughput."],
        "failure_handling": ["Manual offset commits after successful writes."],
        "assumptions": ["Assuming a single Azure region for the MVP."],
    }

    def build(cfg):  # noqa: ANN001
        from app.ai.gateway import AIGateway
        from tests.fakes import FakeChatProvider, FakeEmbeddingProvider

        # enrich_package_summary and the interview calls need a benign
        # payload too; complete_json returns whichever dict this fake holds,
        # so give it the union of keys every caller in this flow reads.
        payload = {
            **hld_payload,
            "intro": "Hi",
            "rewrites": {},
            "sufficient": True,
            "followup": None,
            "reply": "ok",
            "executive_summary": "Event-driven AKS platform with Kafka.",
        }
        return AIGateway(cfg, FakeChatProvider(json_response=payload), FakeEmbeddingProvider())

    monkeypatch.setattr("app.modules.requirements.service.build_gateway", build)
    monkeypatch.setattr("app.modules.options.service.build_gateway", build)

    pid = _project(client)
    client.post(f"/api/v1/projects/{pid}/interview/analyze")
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    pkg = client.post(f"/api/v1/projects/{pid}/package/generate")
    assert pkg.status_code == 200, pkg.text
    body = pkg.json()["data"]
    assert body["provenance"]["hld_source"] == "ai"
    assert body["provenance"]["hld_model"]
    assert "The ingest service validates and partitions events." in body["hld_markdown"]


def test_package_provenance_reports_template_hld_source_on_ai_failure(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    build, _ = _fake_gateway({}, raise_on_json=True)
    monkeypatch.setattr("app.modules.options.service.build_gateway", build)

    pid = _project(client)
    client.post(f"/api/v1/projects/{pid}/interview/analyze")
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    pkg = client.post(f"/api/v1/projects/{pid}/package/generate")
    assert pkg.status_code == 200, pkg.text
    body = pkg.json()["data"]
    assert body["provenance"]["hld_source"] == "template"
    assert body["provenance"]["hld_model"] is None


def test_package_survives_unexpected_exception_in_hld_path(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-provider exception (a bug, not a network/timeout failure) from the
    AI HLD path must not 500 the whole /package/generate request — it's the
    call site's last-resort safety net, distinct from complete_json_with_fallback's
    own internal provider-error handling which only catches the known tuple."""

    class _WeirdBug(Exception):
        """Stands in for an unexpected exception outside _AI_PROVIDER_ERRORS."""

    class _SelectivelyBrokenChat(FakeChatProvider):
        def complete_json(self, messages, schema, *, timeout_s=None):  # noqa: ANN001
            if "component_responsibilities" in (schema.get("properties") or {}):
                raise _WeirdBug("unexpected bug in HLD generation")
            return super().complete_json(messages, schema, timeout_s=timeout_s)

    def build(cfg):  # noqa: ANN001
        payload = {
            "intro": "Hi",
            "rewrites": {},
            "sufficient": True,
            "followup": None,
            "reply": "ok",
            "executive_summary": "Event-driven AKS platform with Kafka.",
        }
        chat = _SelectivelyBrokenChat(json_response=payload)
        return AIGateway(cfg, chat, FakeEmbeddingProvider())

    monkeypatch.setattr("app.modules.requirements.service.build_gateway", build)
    monkeypatch.setattr("app.modules.options.service.build_gateway", build)

    pid = _project(client)
    client.post(f"/api/v1/projects/{pid}/interview/analyze")
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    pkg = client.post(f"/api/v1/projects/{pid}/package/generate")
    assert pkg.status_code == 200, pkg.text
    body = pkg.json()["data"]
    assert body["provenance"]["hld_source"] == "template"
    assert body["provenance"]["hld_model"] is None
    assert body["hld_markdown"]


def test_knowledge_capture_uses_template_hld_not_ai_output(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, db
) -> None:
    """The knowledge corpus that grounds FUTURE HLD generations must never
    accumulate AI-recycled content — even when the served package's HLD came
    from the AI path, the captured excerpt must be the deterministic template's
    output."""
    from app.db.models import KnowledgeDocumentRow

    hld_payload = {
        "component_responsibilities": ["The ingest service validates and partitions events."],
        "technology_choices": [
            {"area": "streaming", "technology": "Apache Kafka", "why": "evidenced in constraints"}
        ],
        "integration_patterns": ["Producers publish to one topic per event type."],
        "data_ownership": ["Kafka is the durable log; Postgres holds read state."],
        "api_event_boundaries": ["Partners never see internal topic names."],
        "scaling_availability": ["Partition count scales with producer throughput."],
        "failure_handling": ["Manual offset commits after successful writes."],
        "assumptions": ["Assuming a single Azure region for the MVP."],
    }

    def build(cfg):  # noqa: ANN001
        payload = {
            **hld_payload,
            "intro": "Hi",
            "rewrites": {},
            "sufficient": True,
            "followup": None,
            "reply": "ok",
            "executive_summary": "Event-driven AKS platform with Kafka.",
        }
        return AIGateway(cfg, FakeChatProvider(json_response=payload), FakeEmbeddingProvider())

    monkeypatch.setattr("app.modules.requirements.service.build_gateway", build)
    monkeypatch.setattr("app.modules.options.service.build_gateway", build)

    pid = _project(client)
    client.post(f"/api/v1/projects/{pid}/interview/analyze")
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    pkg = client.post(f"/api/v1/projects/{pid}/package/generate")
    assert pkg.status_code == 200, pkg.text
    body = pkg.json()["data"]
    # Sanity: the served HLD really did come from the AI path.
    assert body["provenance"]["hld_source"] == "ai"
    assert "The ingest service validates and partitions events." in body["hld_markdown"]

    doc = (
        db.query(KnowledgeDocumentRow)
        .filter(KnowledgeDocumentRow.source_class == "project")
        .order_by(KnowledgeDocumentRow.created_at.desc())
        .first()
    )
    assert doc is not None
    # The captured excerpt must NOT contain the AI-only content...
    assert "The ingest service validates and partitions events." not in doc.content
    # ...and must contain the deterministic template's distinctive section instead.
    assert "## Component responsibilities" in doc.content or "Suggested next step" in doc.content
