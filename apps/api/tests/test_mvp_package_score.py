"""MVP package completeness — quality score, backlog, STRIDE-lite (package.v8)."""

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
            "scale_availability": "5k events/sec · RTO 15 min · RPO 1 min",
            "tech_constraints": "Spring Boot, Kafka, AKS",
            "stack_tags": ["azure", "kafka", "spring-boot"],
        },
    )
    assert res.status_code == 201, res.text
    pid = res.json()["data"]["id"]
    analyzed = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    answers = {
        "rto_rpo": "RTO 15 min · RPO 1 min",
        "peak_traffic": "Peak 5k events/sec sustained",
        "data_residency": "No specific residency constraints; US regions only",
        "auth_model": "OIDC via Entra ID for partners",
        "consistency": "Postgres is the system of record",
        "cloud": "Azure eastus and westus2",
        "user_roles": "Payment operators submit batches, a reviewer approves exceptions, auditors read history",
        "business_rules": "Rules: auto-approve payments under 5,000 when validation passes; above that a human reviewer decides",
        "exception_handling": "Invalid input is rejected with the failing fields; a failed dependency retries three times then queues for manual review",
        "success_metrics": "60% of payments settle untouched, median cycle time under 10 minutes",
        "implementation_language": "Java 21 with Spring Boot; the team is strongest in Java",
    }
    for q in analyzed["questions"]:
        if q["status"] != "open":
            continue
        answer = answers.get(q["code"]) or (
            f"Architecture decision for {q['code']}: documented for package."
        )
        res = client.post(
            f"/api/v1/projects/{pid}/interview/answer",
            json={"question_id": q["id"], "answer": answer},
        )
        assert res.status_code == 200, res.text
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    pkg = client.post(f"/api/v1/projects/{pid}/package/generate")
    assert pkg.status_code == 200, pkg.text
    return pid, pkg.json()["data"]


def test_package_includes_score_backlog_and_threats(client: TestClient) -> None:
    _, body = _packaged(client)
    assert body["provenance"]["workflow_version"] == "package.v8"
    score = body["quality_score"]
    assert score["overall"] in {"missing", "partial", "evidenced", "verified"}
    assert score["categories"]
    assert all("coverage" in c and "score" not in c for c in score["categories"])
    assert "missing_evidence" in score
    assert score.get("label") == "evidence_checklist"
    assert len(body["backlog"]) >= 3
    assert all("priority" in b and "title" in b for b in body["backlog"])
    assert len(body["threats"]) >= 3
    assert any(t.get("stride") for t in body["threats"])


def test_export_includes_backlog_threats_score(client: TestClient) -> None:
    pid, _ = _packaged(client)
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
    paths = {f["path"] for f in res.json()["data"]["files"]}
    assert "backlog/implementation.md" in paths
    assert "threats/stride-lite.md" in paths
    assert "score/architecture-quality.md" in paths


def test_project_dashboard_surfaces_score_and_decisions(client: TestClient) -> None:
    pid, _ = _packaged(client)
    dash = client.get(f"/api/v1/projects/{pid}/dashboard")
    assert dash.status_code == 200, dash.text
    data = dash.json()["data"]
    assert data["lifecycle"]["stage"] in {
        "package",
        "export",
        "options",
        "interview",
        "intake",
    }
    assert data["quality_score"]["overall"] in {
        "missing",
        "partial",
        "evidenced",
        "verified",
    }
    assert data["decisions"]
    assert data["open_risks"]
    assert data["continue_path"].startswith("/projects/")
