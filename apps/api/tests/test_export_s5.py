"""S5 — export Markdown / Mermaid / project JSON (folder or zip)."""

from __future__ import annotations

import io
import zipfile

from fastapi.testclient import TestClient


def _packaged_project(client: TestClient) -> str:
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
    return pid


def test_export_requires_package(client: TestClient) -> None:
    res = client.post(
        "/api/v1/projects",
        json={"name": "Empty", "preferred_cloud": "Azure"},
    )
    pid = res.json()["data"]["id"]
    blocked = client.post(
        f"/api/v1/projects/{pid}/exports",
        json={"layout": "folder"},
    )
    assert blocked.status_code == 409, blocked.text


def test_export_folder_includes_hld_mermaid_project_json(client: TestClient) -> None:
    pid = _packaged_project(client)
    res = client.post(
        f"/api/v1/projects/{pid}/exports",
        json={
            "layout": "folder",
            "include_hld": True,
            "include_mermaid": True,
            "include_adrs": True,
            "include_risks": True,
            "include_project_json": True,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()["data"]
    assert body["layout"] == "folder"
    assert body["status"] == "ready"
    paths = {f["path"] for f in body["files"]}
    assert "README.md" in paths
    assert "hld/architecture.md" in paths
    assert "diagrams/c4-context.mmd" in paths
    assert "project.json" in paths
    assert "decisions/README.md" in paths
    assert "risks/README.md" in paths

    hld = next(f for f in body["files"] if f["path"] == "hld/architecture.md")
    assert (
        "High-level design" in hld["content"]
        or "Architecture" in hld["content"]
        or "HLD" in hld["content"]
    )
    mmd = next(f for f in body["files"] if f["path"] == "diagrams/c4-context.mmd")
    assert "C4Context" in mmd["content"] or "flowchart" in mmd["content"]
    proj = next(f for f in body["files"] if f["path"] == "project.json")
    assert "AKS Event Platform" in proj["content"]


def test_export_zip_download(client: TestClient) -> None:
    pid = _packaged_project(client)
    created = client.post(
        f"/api/v1/projects/{pid}/exports",
        json={"layout": "zip", "include_hld": True, "include_mermaid": True, "include_project_json": True},
    )
    assert created.status_code == 201, created.text
    eid = created.json()["data"]["id"]

    dl = client.get(f"/api/v1/projects/{pid}/exports/{eid}/download")
    assert dl.status_code == 200, dl.text
    assert "zip" in dl.headers.get("content-type", "")
    zf = zipfile.ZipFile(io.BytesIO(dl.content))
    names = set(zf.namelist())
    assert "hld/architecture.md" in names
    assert "diagrams/c4-context.mmd" in names
    assert "project.json" in names


def test_list_and_get_export(client: TestClient) -> None:
    pid = _packaged_project(client)
    created = client.post(
        f"/api/v1/projects/{pid}/exports",
        json={"layout": "folder"},
    ).json()["data"]
    listed = client.get(f"/api/v1/projects/{pid}/exports")
    assert listed.status_code == 200
    assert any(e["id"] == created["id"] for e in listed.json()["data"])

    detail = client.get(f"/api/v1/projects/{pid}/exports/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["data"]["files"]
