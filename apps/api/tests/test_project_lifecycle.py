"""Project lifecycle — derived from persisted workflow artifacts."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create(client: TestClient, name: str = "Lifecycle Demo") -> str:
    res = client.post(
        "/api/v1/projects",
        json={
            "name": name,
            "description": "Payments",
            "stack_tags": ["azure", "kafka"],
            "business_objective": "Process payments",
            "preferred_cloud": "azure",
            "scale_availability": "high",
            "tech_constraints": "Java Spring Boot on AKS",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["data"]["id"]


def _answer_all(client: TestClient, pid: str) -> None:
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
    analyzed = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    for q in analyzed["questions"]:
        if q["status"] != "open":
            continue
        answer = answers.get(q["code"]) or (
            f"Architecture decision for {q['code']}: documented for lifecycle."
        )
        res = client.post(
            f"/api/v1/projects/{pid}/interview/answer",
            json={"question_id": q["id"], "answer": answer},
        )
        assert res.status_code == 200, res.text


def test_new_project_starts_at_intake(client: TestClient) -> None:
    pid = _create(client)
    got = client.get(f"/api/v1/projects/{pid}").json()["data"]
    life = got["lifecycle"]
    assert life["stage"] == "intake"
    assert life["label"]
    assert life["continue_path"] == f"/projects/{pid}/interview"
    assert life["milestones"]["intake_done"] is True
    assert life["milestones"]["interview_started"] is False
    assert life["milestones"]["options_ready"] is False


def test_lifecycle_advances_through_workflow(client: TestClient) -> None:
    pid = _create(client)

    client.post(f"/api/v1/projects/{pid}/interview/analyze")
    after_interview = client.get(f"/api/v1/projects/{pid}").json()["data"]["lifecycle"]
    assert after_interview["stage"] == "interview"
    assert after_interview["milestones"]["interview_started"] is True
    assert after_interview["continue_path"] == f"/projects/{pid}/interview"

    _answer_all(client, pid)
    ready = client.get(f"/api/v1/projects/{pid}").json()["data"]["lifecycle"]
    assert ready["milestones"]["interview_ready"] is True
    assert ready["continue_path"] == f"/projects/{pid}/options"

    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    after_opts = client.get(f"/api/v1/projects/{pid}").json()["data"]["lifecycle"]
    assert after_opts["stage"] == "options"
    assert after_opts["milestones"]["options_ready"] is True
    assert after_opts["continue_path"] == f"/projects/{pid}/options"

    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    selected = client.get(f"/api/v1/projects/{pid}").json()["data"]["lifecycle"]
    assert selected["milestones"]["option_selected"] is True
    assert selected["stage"] == "options"

    client.post(f"/api/v1/projects/{pid}/package/generate")
    after_pkg = client.get(f"/api/v1/projects/{pid}").json()["data"]["lifecycle"]
    assert after_pkg["stage"] == "package"
    assert after_pkg["milestones"]["package_ready"] is True
    assert after_pkg["continue_path"] == f"/projects/{pid}/export"

    client.post(
        f"/api/v1/projects/{pid}/exports",
        json={"layout": "folder"},
    )
    after_export = client.get(f"/api/v1/projects/{pid}").json()["data"]["lifecycle"]
    assert after_export["stage"] == "export"
    assert after_export["milestones"]["export_done"] is True
    assert after_export["continue_path"] == f"/projects/{pid}/package"


def test_list_projects_includes_lifecycle(client: TestClient) -> None:
    pid = _create(client, "Listed Lifecycle")
    client.post(f"/api/v1/projects/{pid}/interview/analyze")
    listed = client.get("/api/v1/projects").json()["data"]
    match = next(p for p in listed if p["id"] == pid)
    assert match["lifecycle"]["stage"] == "interview"
    assert match["lifecycle"]["continue_path"].endswith("/interview")


def test_regenerate_options_regresses_package_stage(client: TestClient) -> None:
    pid = _create(client)
    _answer_all(client, pid)
    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    client.post(f"/api/v1/projects/{pid}/package/generate")
    assert client.get(f"/api/v1/projects/{pid}").json()["data"]["lifecycle"]["stage"] == "package"

    client.post(f"/api/v1/projects/{pid}/options/generate")
    life = client.get(f"/api/v1/projects/{pid}").json()["data"]["lifecycle"]
    assert life["stage"] == "options"
    assert life["milestones"]["package_ready"] is False
    assert life["milestones"]["option_selected"] is False
