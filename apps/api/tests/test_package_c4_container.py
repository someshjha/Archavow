"""Package C4 container Mermaid (package.v8) + export path."""

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


def test_package_includes_c4_container_mermaid(client: TestClient) -> None:
    _, body = _packaged(client)
    assert body["provenance"]["workflow_version"] == "package.v8"
    assert "C4Context" in body["mermaid"]
    assert "C4Container" in body["mermaid_container"]
    assert "Container(" in body["mermaid_container"] or "ContainerDb" in body["mermaid_container"] or "ContainerQueue" in body["mermaid_container"]
    assert "Container_Queue" not in body["mermaid_container"]
    assert body["mermaid_sequence"]
    assert not (body.get("mermaid_deploy") or "").strip()
    assert (body.get("documents") or {}).get("diagram_dataflow")


def test_export_includes_c4_container_file(client: TestClient) -> None:
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
    assert "diagrams/c4-container.mmd" in paths
    assert "diagrams/sequence.mmd" in paths
    assert "diagrams/data-flow.mmd" in paths
    assert "diagrams/deploy.mmd" not in paths
