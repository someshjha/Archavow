"""Interview API — scorecard payload, options gate, and the answer-box preview."""

from __future__ import annotations

from fastapi.testclient import TestClient

ANSWERS: dict[str, str] = {
    "current_approach": "Adjusters key claims into a legacy AS/400 form and email spreadsheets",
    "functional_scope": "Intake a claim, validate the policy, score it, adjudicate, and pay",
    "user_roles": "Claimants submit claims, adjusters review exceptions, auditors read history",
    "business_rules": "Auto-approve claims under 2,500 when the policy is active; above that an adjuster decides",
    "exception_handling": "Invalid input is rejected with the failing fields; a failed dependency retries three times then queues for manual review",
    "success_metrics": "70% of claims adjudicate untouched, median cycle time under 4 hours",
    "implementation_language": "Java 21 with Spring Boot; the team is strongest in Java",
    "integrations": "Guidewire policy admin, Stripe payouts, and the fraud scoring API",
    "team_constraints": "Six engineers, two of them senior, delivering in nine months",
    "rto_rpo": "RTO 15 min · RPO 1 min",
    "peak_traffic": "Peak 5k events/sec sustained",
    "consistency": "Postgres is the system of record",
    "cloud": "Azure eastus and westus2",
    "auth_model": "OIDC via Entra ID for partners, mTLS between services",
    "data_residency": "Claims data stays in US regions; no EU residency constraint",
}


def _create(client: TestClient, name: str = "Claims Intake") -> str:
    res = client.post(
        "/api/v1/projects",
        json={
            "name": name,
            "description": "Claims intake and automated adjudication",
            "stack_tags": ["azure"],
            "business_objective": "Adjudicate claims without manual keying",
            "problem_statement": "Adjusters rekey every claim by hand",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["data"]["id"]


def _answer(client: TestClient, pid: str, question: dict) -> dict:
    answer = ANSWERS.get(question["code"]) or (
        f"Documented decision for {question['code']} with concrete detail."
    )
    res = client.post(
        f"/api/v1/projects/{pid}/interview/answer",
        json={"question_id": question["id"], "answer": answer},
    )
    assert res.status_code == 200, res.text
    return res.json()["data"]


def _answer_codes(client: TestClient, pid: str, codes: set[str]) -> dict:
    state = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    for question in state["questions"]:
        if question["status"] == "open" and question["code"] in codes:
            state = _answer(client, pid, question)
    return state


def test_analyze_returns_five_categories_and_gate_state(client: TestClient) -> None:
    pid = _create(client)
    body = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    comp = body["completeness"]

    assert [c["label"] for c in comp["categories"]] == [
        "Scope",
        "Story readiness",
        "Reliability",
        "Security & compliance",
        "Delivery",
    ]
    assert comp["ready"] is False
    assert [c["key"] for c in comp["unlock"] if not c["ok"]]
    story = next(c for c in comp["categories"] if c["key"] == "story_readiness")
    assert story["floor"] == 75
    assert "business rules" in story["open_labels"]


def test_active_question_comes_from_the_weakest_category(client: TestClient) -> None:
    pid = _create(client)
    # Close every bucket except Security & compliance.
    state = _answer_codes(client, pid, set(ANSWERS) - {"auth_model", "data_residency"})

    comp = state["completeness"]
    security = next(c for c in comp["categories"] if c["key"] == "security_compliance")
    assert security["score"] == 0
    assert state["active_question"]["code"] in {"auth_model", "data_residency"}


def test_answer_box_preview_matches_the_score_it_produces(client: TestClient) -> None:
    """The preview promises exact numbers, so answering must land on them."""
    pid = _create(client)
    state = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    impact = state["next_impact"]
    assert impact is not None
    assert impact["code"] == state["active_question"]["code"]

    after = _answer(client, pid, state["active_question"])
    comp = after["completeness"]
    moved = next(c for c in comp["categories"] if c["key"] == impact["category_key"])
    assert moved["score"] == impact["category_to"]
    assert comp["overall"] == impact["overall_to"]


def test_options_stay_locked_until_every_floor_is_met(client: TestClient) -> None:
    pid = _create(client)
    state = _answer_codes(client, pid, set(ANSWERS) - {"auth_model", "data_residency"})

    comp = state["completeness"]
    assert comp["overall"] >= 70
    assert comp["ready"] is False
    assert [c["key"] for c in comp["unlock"] if not c["ok"]] == ["security_compliance"]
    life = client.get(f"/api/v1/projects/{pid}").json()["data"]["lifecycle"]
    assert life["milestones"]["interview_ready"] is False

    state = _answer_codes(client, pid, {"auth_model", "data_residency"})
    assert state["completeness"]["ready"] is True
    life = client.get(f"/api/v1/projects/{pid}").json()["data"]["lifecycle"]
    assert life["milestones"]["interview_ready"] is True
