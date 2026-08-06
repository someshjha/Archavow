"""Package generate must tolerate long interview answers (SearchRequest 4k cap)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_package_generate_truncates_long_search_query(client: TestClient) -> None:
    res = client.post(
        "/api/v1/projects",
        json={
            "name": "Long Interview Project",
            "business_objective": "Process events",
            "problem_statement": "Need reliability",
            "preferred_cloud": "Azure",
            "scale_availability": "5k/sec",
            "tech_constraints": "Kafka, AKS",
            "stack_tags": ["azure", "kafka"],
        },
    )
    assert res.status_code == 201, res.text
    pid = res.json()["data"]["id"]
    analyzed = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    # Answers that satisfy gap checks, padded past the 4k knowledge-search bound.
    pad = " Additional operational context for the architecture package. " * 80
    answers = {
        "rto_rpo": f"RTO 15 min · RPO 1 min.{pad}",
        "peak_traffic": f"Peak 5k events/sec sustained.{pad}",
        "data_residency": f"No specific residency constraints; US regions only.{pad}",
        "auth_model": f"OIDC via Entra ID for partners.{pad}",
        "consistency": f"Postgres is the system of record.{pad}",
        "cloud": f"Azure eastus and westus2.{pad}",
        "user_roles": f"Payment operators submit batches, a reviewer approves exceptions, auditors read history.{pad}",
        "business_rules": f"Rules: auto-approve payments under 5,000 when validation passes; above that a human reviewer decides.{pad}",
        "exception_handling": f"Invalid input is rejected with the failing fields; a failed dependency retries three times then queues for manual review.{pad}",
        "success_metrics": f"60% of payments settle untouched, median cycle time under 10 minutes.{pad}",
        "implementation_language": f"Java 21 with Spring Boot; the team is strongest in Java.{pad}",
    }
    for q in analyzed["questions"]:
        if q["status"] != "open":
            continue
        answer = answers.get(q["code"]) or (
            f"Architecture decision for {q['code']}: documented for package.{pad}"
        )
        ans = client.post(
            f"/api/v1/projects/{pid}/interview/answer",
            json={"question_id": q["id"], "answer": answer[:8000]},
        )
        assert ans.status_code == 200, ans.text

    opts = client.post(f"/api/v1/projects/{pid}/options/generate").json()["data"]["options"]
    assert opts
    selected = client.post(f"/api/v1/projects/{pid}/options/{opts[0]['id']}/select")
    assert selected.status_code == 200, selected.text
    pkg = client.post(f"/api/v1/projects/{pid}/package/generate")
    assert pkg.status_code == 200, pkg.text
    assert pkg.json()["data"]["hld_markdown"]
