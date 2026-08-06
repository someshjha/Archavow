"""Package includes sequence + deploy Mermaid (package.v8)."""

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
            "scale_availability": "5k events/sec",
            "tech_constraints": "Spring Boot, Kafka, AKS",
        },
    )
    assert res.status_code == 201
    pid = res.json()["data"]["id"]
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    pkg = client.post(f"/api/v1/projects/{pid}/package/generate")
    assert pkg.status_code == 200, pkg.text
    return pid, pkg.json()["data"]


def test_package_includes_sequence_and_dataflow_mermaid(client: TestClient) -> None:
    _, body = _packaged(client)
    assert body["provenance"]["workflow_version"] == "package.v8"
    assert "C4Context" in body["mermaid"] or "flowchart" in body["mermaid"]
    assert "sequenceDiagram" in body["mermaid_sequence"]
    assert "participant" in body["mermaid_sequence"] or "->" in body["mermaid_sequence"]
    # Deployment topology was removed; data-flow carries the labeled path.
    assert not (body.get("mermaid_deploy") or "").strip()
    docs = body.get("documents") or {}
    flow = docs.get("diagram_dataflow") or ""
    assert "flowchart" in flow
    assert "Authoritative write" in flow or "Persist outcome" in flow
    joined = (body["mermaid_sequence"] + flow).lower()
    assert "kafka" in joined or "api" in joined or "postgres" in joined


def test_export_includes_sequence_and_dataflow_files(client: TestClient) -> None:
    pid, _ = _packaged(client)
    res = client.post(
        f"/api/v1/projects/{pid}/exports",
        json={
            "layout": "folder",
            "include_hld": False,
            "include_mermaid": True,
            "include_adrs": False,
            "include_risks": False,
            "include_project_json": False,
        },
    )
    assert res.status_code == 201, res.text
    paths = {f["path"] for f in res.json()["data"]["files"]}
    assert "diagrams/c4-context.mmd" in paths
    assert "diagrams/sequence.mmd" in paths
    assert "diagrams/data-flow.mmd" in paths
    assert "diagrams/deploy.mmd" not in paths
