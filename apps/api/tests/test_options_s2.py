"""S2 — architecture options + human-gate select."""

from __future__ import annotations

from fastapi.testclient import TestClient


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
    assert res.status_code == 201, res.text
    pid = res.json()["data"]["id"]
    # Close key gaps so options can reference NFRs
    analyzed = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    rto = next((q for q in analyzed["questions"] if q["code"] == "rto_rpo"), None)
    if rto:
        client.post(
            f"/api/v1/projects/{pid}/interview/answer",
            json={"question_id": rto["id"], "answer": "RTO 15 min · RPO 1 min"},
        )
    return pid


def test_generate_options_returns_three_scored_alternatives(client: TestClient) -> None:
    pid = _ready_project(client)
    res = client.post(f"/api/v1/projects/{pid}/options/generate")
    assert res.status_code == 200, res.text
    body = res.json()["data"]
    assert len(body["options"]) == 3
    titles = {o["title"] for o in body["options"]}
    assert any("Kafka" in t or "AKS" in t for t in titles)
    assert sum(1 for o in body["options"] if o["recommended"]) == 1
    for opt in body["options"]:
        assert opt["fit_score"] >= 1
        assert opt.get("origin") in {"template", "ai"}
        assert len(opt["pros"]) >= 2
        assert len(opt["cons"]) >= 2
        assert opt["cost_band"]
        assert opt["ops_band"]
        assert opt["summary"]
    assert body["selected_option_id"] is None
    # Deterministic fallback path should label templates
    if body.get("ai_assist", {}).get("detail", "").find("deterministic") >= 0 or body[
        "ai_assist"
    ].get("status") in {"skipped", "failed"}:
        assert all(o["origin"] == "template" for o in body["options"])
        assert any(
            "starter template" in o["summary"].lower() or "working draft" in o["summary"].lower()
            for o in body["options"]
        )


def test_list_options_after_generate(client: TestClient) -> None:
    pid = _ready_project(client)
    client.post(f"/api/v1/projects/{pid}/options/generate")
    res = client.get(f"/api/v1/projects/{pid}/options")
    assert res.status_code == 200
    assert len(res.json()["data"]["options"]) == 3


def test_select_option_is_human_gate(client: TestClient) -> None:
    pid = _ready_project(client)
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    chosen = opts[0]["id"]

    # Package before select must fail
    blocked = client.post(f"/api/v1/projects/{pid}/package/generate")
    assert blocked.status_code == 409, blocked.text

    selected = client.post(f"/api/v1/projects/{pid}/options/{chosen}/select")
    assert selected.status_code == 200, selected.text
    data = selected.json()["data"]
    assert data["selected_option_id"] == chosen
    assert any(o["id"] == chosen and o["selected"] for o in data["options"])
    assert sum(1 for o in data["options"] if o["selected"]) == 1

    # Re-fetch
    listed = client.get(f"/api/v1/projects/{pid}/options").json()["data"]
    assert listed["selected_option_id"] == chosen


def test_package_generate_after_select(client: TestClient) -> None:
    pid = _ready_project(client)
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")

    pkg = client.post(f"/api/v1/projects/{pid}/package/generate")
    assert pkg.status_code == 200, pkg.text
    body = pkg.json()["data"]
    assert body["status"] == "draft"
    assert body["option_id"] == opts[0]["id"]
    assert (
        "High-level design" in body["hld_markdown"]
        or "Architecture" in body["hld_markdown"]
        or "HLD" in body["hld_markdown"]
    )
    assert body.get("documents", {}).get("overview")
    assert body.get("documents", {}).get("roadmap")
    assert "mermaid" in body
    assert "C4Context" in body["mermaid"] or "flowchart" in body["mermaid"]
    assert body["provenance"]["workflow_version"]
    assert body["provenance"]["chat_provider"]

    got = client.get(f"/api/v1/projects/{pid}/package")
    assert got.status_code == 200
    assert got.json()["data"]["status"] == "draft"


def test_regenerate_options_clears_selection(client: TestClient) -> None:
    pid = _ready_project(client)
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    again = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]
    assert again["selected_option_id"] is None
    assert all(not o["selected"] for o in again["options"])


def test_reselect_same_option_keeps_package(client: TestClient) -> None:
    pid = _ready_project(client)
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    chosen = opts[0]["id"]
    client.post(f"/api/v1/projects/{pid}/options/{chosen}/select")
    pkg = client.post(f"/api/v1/projects/{pid}/package/generate").json()["data"]
    pkg_id = pkg["id"]

    again = client.post(f"/api/v1/projects/{pid}/options/{chosen}/select")
    assert again.status_code == 200
    kept = client.get(f"/api/v1/projects/{pid}/package")
    assert kept.status_code == 200
    assert kept.json()["data"]["id"] == pkg_id


def test_switch_option_clears_package(client: TestClient) -> None:
    pid = _ready_project(client)
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    client.post(f"/api/v1/projects/{pid}/package/generate")
    client.post(f"/api/v1/projects/{pid}/options/{opts[1]['id']}/select")
    gone = client.get(f"/api/v1/projects/{pid}/package")
    assert gone.status_code == 404
