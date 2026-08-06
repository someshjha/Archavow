"""Package ADRs + risk register (deterministic package.v1)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _packaged(client: TestClient) -> tuple[str, dict]:
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
    assert res.status_code == 201, res.text
    pid = res.json()["data"]["id"]
    analyzed = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    rto = next((q for q in analyzed["questions"] if q["code"] == "rto_rpo"), None)
    if rto:
        client.post(
            f"/api/v1/projects/{pid}/interview/answer",
            json={"question_id": rto["id"], "answer": "RTO 15 min · RPO 1 min"},
        )
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    pkg = client.post(f"/api/v1/projects/{pid}/package/generate")
    assert pkg.status_code == 200, pkg.text
    return pid, pkg.json()["data"]


def test_package_includes_adrs_and_risks(client: TestClient) -> None:
    _, body = _packaged(client)
    assert body["provenance"]["workflow_version"] == "package.v8"
    assert len(body["adrs"]) >= 1
    adr = body["adrs"][0]
    assert adr["id"].startswith("ADR-")
    assert adr["title"]
    assert adr["status"] in {"accepted", "proposed"}
    assert adr["context"]
    assert adr["decision"]
    assert len(adr["consequences"]) >= 1

    assert len(body["risks"]) >= 2
    risk = body["risks"][0]
    assert risk["id"].startswith("R-")
    assert risk["title"]
    assert risk["severity"] in {"high", "medium", "low"}
    assert risk["impact"]
    assert risk["mitigation"]


def test_export_writes_adr_and_risk_markdown(client: TestClient) -> None:
    pid, _ = _packaged(client)
    res = client.post(
        f"/api/v1/projects/{pid}/exports",
        json={
            "layout": "folder",
            "include_hld": True,
            "include_mermaid": False,
            "include_adrs": True,
            "include_risks": True,
            "include_project_json": False,
        },
    )
    assert res.status_code == 201, res.text
    paths = {f["path"] for f in res.json()["data"]["files"]}
    assert any(p.startswith("decisions/ADR-") and p.endswith(".md") for p in paths)
    assert "risks/register.md" in paths
    risks = next(f for f in res.json()["data"]["files"] if f["path"] == "risks/register.md")
    assert "R-001" in risks["content"] or "Mitigation" in risks["content"]
