"""Projects + Settings HTTP API — requires Postgres (see client fixture)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_list_get_project(client: TestClient) -> None:
    created = client.post(
        "/api/v1/projects",
        json={
            "name": "AKS Event Platform",
            "description": "Payments on Kafka",
            "stack_tags": ["azure", "kafka", "spring-boot"],
        },
    )
    assert created.status_code == 201, created.text
    project = created.json().get("data", created.json())
    assert project["id"]
    assert project["name"] == "AKS Event Platform"
    assert "azure" in project.get("stack_tags", [])

    listed = client.get("/api/v1/projects")
    assert listed.status_code == 200
    items = listed.json().get("data", listed.json())
    if isinstance(items, dict):
        items = items.get("items", items.get("projects", []))
    assert any(p["id"] == project["id"] for p in items)

    got = client.get(f"/api/v1/projects/{project['id']}")
    assert got.status_code == 200
    assert got.json().get("data", got.json())["name"] == "AKS Event Platform"


def test_create_project_requires_name(client: TestClient) -> None:
    res = client.post("/api/v1/projects", json={"description": "no name"})
    assert res.status_code == 422


def test_create_project_rejects_oversized_fields(client: TestClient) -> None:
    res = client.post(
        "/api/v1/projects",
        json={
            "name": "x" * 257,
            "preferred_cloud": "y" * 65,
        },
    )
    assert res.status_code == 422


def test_delete_project_removes_project_and_cascades(client: TestClient) -> None:
    created = client.post(
        "/api/v1/projects",
        json={
            "name": "Disposable Project",
            "preferred_cloud": "Azure",
            "tech_constraints": "Spring Boot, Postgres",
        },
    )
    assert created.status_code == 201, created.text
    pid = created.json()["data"]["id"]

    # Seed child rows so CASCADE is exercised, not just the empty project.
    assert client.post(f"/api/v1/projects/{pid}/interview/analyze").status_code == 200
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    assert opts
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    assert client.post(f"/api/v1/projects/{pid}/package/generate").status_code == 200

    deleted = client.delete(f"/api/v1/projects/{pid}")
    assert deleted.status_code == 204, deleted.text

    assert client.get(f"/api/v1/projects/{pid}").status_code == 404
    assert client.get(f"/api/v1/projects/{pid}/package").status_code == 404
    listed = client.get("/api/v1/projects").json()["data"]
    assert all(p["id"] != pid for p in listed)


def test_delete_project_missing_returns_404(client: TestClient) -> None:
    res = client.delete("/api/v1/projects/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404


def test_delete_project_invalid_id_returns_404(client: TestClient) -> None:
    res = client.delete("/api/v1/projects/not-a-uuid")
    assert res.status_code == 404
