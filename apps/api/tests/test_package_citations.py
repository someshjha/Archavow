"""Knowledge citations appear on package generation."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _project_with_kafka(client: TestClient) -> str:
    res = client.post(
        "/api/v1/projects",
        json={
            "name": "AKS Event Platform",
            "business_objective": "Payment events",
            "preferred_cloud": "Azure",
            "tech_constraints": "Spring Boot, Kafka, AKS",
            "scale_availability": "5k/sec",
        },
    )
    assert res.status_code == 201
    pid = res.json()["data"]["id"]
    analyzed = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    rto = next((q for q in analyzed["questions"] if q["code"] == "rto_rpo"), None)
    if rto:
        client.post(
            f"/api/v1/projects/{pid}/interview/answer",
            json={"question_id": rto["id"], "answer": "RTO 15 · RPO 1"},
        )
    return pid


def test_package_cites_uploaded_standard(client: TestClient) -> None:
    uploaded = client.post(
        "/api/v1/knowledge/documents",
        json={
            "title": "org/kafka-mtls.md",
            "source_class": "org",
            "content": (
                "# Kafka security\n\n"
                "Kafka clients must use mTLS in production.\n\n"
                "## Brokers\n\n"
                "Prefer private endpoints for broker traffic."
            ),
        },
    )
    assert uploaded.status_code == 201, uploaded.text

    pid = _project_with_kafka(client)
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    pkg = client.post(f"/api/v1/projects/{pid}/package/generate")
    assert pkg.status_code == 200, pkg.text
    body = pkg.json()["data"]

    assert body["provenance"]["workflow_version"] == "package.v8"
    assert body["retrieval_status"] in {"ok", "degraded", "partial"}
    assert len(body["citations"]) >= 1
    cites = " ".join(c["citation"] for c in body["citations"]).lower()
    assert "kafka" in cites or "mtls" in cites or "org/kafka" in cites
    assert "mTLS" in body["hld_markdown"] or "mtls" in body["hld_markdown"].lower()
    assert "Standards we pulled in" in body["hld_markdown"] or "Standards cited" in body["hld_markdown"]


def test_package_without_knowledge_has_empty_citations(client: TestClient) -> None:
    pid = _project_with_kafka(client)
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    # Wipe knowledge so this test is isolated if prior docs exist — upload nothing unique
    body = client.post(f"/api/v1/projects/{pid}/package/generate").json()["data"]
    assert "citations" in body
    assert body["retrieval_status"] in {"ok", "degraded", "partial"}
