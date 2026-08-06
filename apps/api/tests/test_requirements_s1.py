"""S1 — project intake + interview gaps (deterministic analyzer)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_sparse_project(client: TestClient) -> str:
    res = client.post(
        "/api/v1/projects",
        json={
            "name": "Claims API modernization",
            "description": "Lift and shift APIs",
            "stack_tags": ["azure", "spring-boot"],
            "business_objective": "Modernize claims processing APIs for the regional carrier",
            "problem_statement": "Legacy nightly batch cannot meet same-day settlement SLAs",
            "preferred_cloud": "Azure",
            "scale_availability": "",
            "tech_constraints": "Spring Boot services running on AKS",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["data"]["id"]


def test_create_project_stores_intake_fields(client: TestClient) -> None:
    res = client.post(
        "/api/v1/projects",
        json={
            "name": "AKS Event Platform",
            "business_objective": "Ingest payment events on Azure",
            "problem_statement": "Batch misses SLAs",
            "preferred_cloud": "Azure",
            "scale_availability": "5k events/sec · 99.9%",
            "tech_constraints": "Spring Boot, Kafka, AKS",
            "stack_tags": ["azure", "kafka"],
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()["data"]
    assert data["business_objective"].startswith("Ingest")
    assert data["preferred_cloud"] == "Azure"
    assert data["tech_constraints"]

    got = client.get(f"/api/v1/projects/{data['id']}")
    assert got.status_code == 200
    body = got.json()["data"]
    assert body["problem_statement"] == "Batch misses SLAs"
    assert body["scale_availability"] == "5k events/sec · 99.9%"


def test_put_intake_updates_project(client: TestClient) -> None:
    pid = _create_sparse_project(client)
    res = client.put(
        f"/api/v1/projects/{pid}/intake",
        json={
            "business_objective": "Updated objective",
            "problem_statement": "Updated problem",
            "preferred_cloud": "Azure",
            "scale_availability": "1k rps",
            "tech_constraints": "AKS",
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["business_objective"] == "Updated objective"


def test_analyze_interview_surfaces_rto_rpo_gap(client: TestClient) -> None:
    pid = _create_sparse_project(client)
    res = client.post(f"/api/v1/projects/{pid}/interview/analyze")
    assert res.status_code == 200, res.text
    body = res.json()["data"]
    assert body["questions"]
    codes = {q["code"] for q in body["questions"]}
    assert "rto_rpo" in codes
    assert any("RTO" in q["prompt"] or "RPO" in q["prompt"] for q in body["questions"])
    assert body["completeness"]["overall"] < 80


def test_solution_questions_come_before_nfr_questions(client: TestClient) -> None:
    pid = _create_sparse_project(client)
    res = client.post(f"/api/v1/projects/{pid}/interview/analyze")
    assert res.status_code == 200, res.text
    codes_in_order = [q["code"] for q in res.json()["data"]["questions"]]
    solution_codes = {"current_approach", "functional_scope", "integrations", "team_constraints"}
    nfr_codes = {"rto_rpo", "peak_traffic", "data_residency", "auth_model", "consistency", "cloud"}
    assert solution_codes <= set(codes_in_order)
    assert nfr_codes <= set(codes_in_order)
    last_solution_idx = max(codes_in_order.index(c) for c in solution_codes)
    first_nfr_idx = min(codes_in_order.index(c) for c in nfr_codes)
    assert last_solution_idx < first_nfr_idx

    active = res.json()["data"]["active_question"]
    assert active["code"] in solution_codes


def test_answer_question_raises_completeness(client: TestClient) -> None:
    pid = _create_sparse_project(client)
    analyzed = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    rto = next(q for q in analyzed["questions"] if q["code"] == "rto_rpo")

    answered = client.post(
        f"/api/v1/projects/{pid}/interview/answer",
        json={
            "question_id": rto["id"],
            "answer": "RTO 15 min · RPO 1 min for payment events",
        },
    )
    assert answered.status_code == 200, answered.text
    data = answered.json()["data"]
    assert data["question"]["status"] == "answered"
    assert data["question"]["answer"]
    # RTO gap closed
    open_codes = {q["code"] for q in data["questions"] if q["status"] == "open"}
    assert "rto_rpo" not in open_codes
    assert data["completeness"]["overall"] > analyzed["completeness"]["overall"]

    # Captured as NFR requirement
    reqs = client.get(f"/api/v1/projects/{pid}/requirements").json()["data"]
    assert any("RTO" in r["text"] or "RPO" in r["text"] for r in reqs)
    rto_req = next(r for r in reqs if r["source"] == "interview:rto_rpo")
    assert rto_req["kind"] == "nfr"


def test_suggest_answer_falls_back_to_deterministic_template(client: TestClient) -> None:
    """No AI configured in tests, so /interview/suggest must still return a usable draft."""
    pid = _create_sparse_project(client)
    analyzed = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    rto = next(q for q in analyzed["questions"] if q["code"] == "rto_rpo")

    res = client.post(
        f"/api/v1/projects/{pid}/interview/suggest",
        json={"question_id": rto["id"]},
    )
    assert res.status_code == 200, res.text
    body = res.json()["data"]
    assert body["source"] == "template"
    assert body["suggestion"]

    # The suggestion is a draft only — it must not itself satisfy the gap
    # until the architect reviews and submits it as their real answer.
    state = client.get(f"/api/v1/projects/{pid}/interview").json()["data"]
    rto_after = next(q for q in state["questions"] if q["code"] == "rto_rpo")
    assert rto_after["status"] == "open"


def test_suggest_answer_has_real_template_for_solution_codes(client: TestClient) -> None:
    """The 4 solution-shaping codes must get a real deterministic starter
    template (like every other code), not the generic 'No draft available'
    placeholder — otherwise Suggest an answer silently degrades for the
    branch's headline questions."""
    pid = _create_sparse_project(client)
    analyzed = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]

    for code in ("current_approach", "functional_scope", "integrations", "team_constraints"):
        question = next(q for q in analyzed["questions"] if q["code"] == code)
        res = client.post(
            f"/api/v1/projects/{pid}/interview/suggest",
            json={"question_id": question["id"]},
        )
        assert res.status_code == 200, res.text
        body = res.json()["data"]
        assert body["source"] == "template"
        assert "No draft available" not in body["suggestion"], code


def test_suggest_answer_unknown_question_404s(client: TestClient) -> None:
    pid = _create_sparse_project(client)
    client.post(f"/api/v1/projects/{pid}/interview/analyze")
    res = client.post(
        f"/api/v1/projects/{pid}/interview/suggest",
        json={"question_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert res.status_code == 404


def test_placeholder_answer_rejected(client: TestClient) -> None:
    pid = _create_sparse_project(client)
    analyzed = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    peak = next(q for q in analyzed["questions"] if q["code"] == "peak_traffic")
    before = analyzed["completeness"]["overall"]

    rejected = client.post(
        f"/api/v1/projects/{pid}/interview/answer",
        json={"question_id": peak["id"], "answer": "TBD"},
    )
    assert rejected.status_code == 422

    state = client.get(f"/api/v1/projects/{pid}/interview").json()["data"]
    peak_after = next(q for q in state["questions"] if q["code"] == "peak_traffic")
    assert peak_after["status"] == "open"
    assert state["completeness"]["overall"] == before


def test_rejected_answer_is_persisted_for_later_rephrasing(client: TestClient) -> None:
    pid = _create_sparse_project(client)
    analyzed = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    peak = next(q for q in analyzed["questions"] if q["code"] == "peak_traffic")

    rejected = client.post(
        f"/api/v1/projects/{pid}/interview/answer",
        json={"question_id": peak["id"], "answer": "somewhere around a few hundred a day I think"},
    )
    assert rejected.status_code == 422

    state = client.get(f"/api/v1/projects/{pid}/interview").json()["data"]
    peak_after = next(q for q in state["questions"] if q["code"] == "peak_traffic")
    assert peak_after["status"] == "open"
    assert peak_after["answer"] == "somewhere around a few hundred a day I think"


def test_answer_upserts_requirement_and_maps_kind(client: TestClient) -> None:
    pid = _create_sparse_project(client)
    analyzed = client.post(f"/api/v1/projects/{pid}/interview/analyze").json()["data"]
    auth = next(q for q in analyzed["questions"] if q["code"] == "auth_model")

    first = client.post(
        f"/api/v1/projects/{pid}/interview/answer",
        json={"question_id": auth["id"], "answer": "OIDC via Entra ID"},
    )
    assert first.status_code == 200, first.text

    # Re-answer (retry / edit) must upsert, not duplicate
    second = client.post(
        f"/api/v1/projects/{pid}/interview/answer",
        json={"question_id": auth["id"], "answer": "mTLS between partners plus OIDC"},
    )
    assert second.status_code == 200, second.text

    reqs = client.get(f"/api/v1/projects/{pid}/requirements").json()["data"]
    auth_reqs = [r for r in reqs if r["source"] == "interview:auth_model"]
    assert len(auth_reqs) == 1
    assert auth_reqs[0]["kind"] == "security"
    assert "mTLS" in auth_reqs[0]["text"]


def test_completeness_endpoint(client: TestClient) -> None:
    pid = _create_sparse_project(client)
    client.post(f"/api/v1/projects/{pid}/interview/analyze")
    res = client.get(f"/api/v1/projects/{pid}/completeness")
    assert res.status_code == 200
    body = res.json()["data"]
    assert "overall" in body
    for key in ("scope", "story_readiness", "reliability", "security_compliance", "delivery"):
        assert key in body
    assert [c["key"] for c in body["categories"]] == [
        "scope",
        "story_readiness",
        "reliability",
        "security_compliance",
        "delivery",
    ]
    assert body["ready"] is False
    assert body["unlock"]
    assert "gaps" in body
    assert "captured" in body


def test_get_interview_state(client: TestClient) -> None:
    pid = _create_sparse_project(client)
    client.post(f"/api/v1/projects/{pid}/interview/analyze")
    res = client.get(f"/api/v1/projects/{pid}/interview")
    assert res.status_code == 200
    body = res.json()["data"]
    assert "questions" in body
    assert "completeness" in body
    assert body["active_question"] is not None


def test_analyze_gaps_returns_codes_in_order(client: TestClient) -> None:
    """Verify analyze_gaps() returns gaps in CODE_ORDER sequence."""
    from app.modules.requirements.gap_analyze import CODE_ORDER, analyze_gaps
    from app.modules.requirements.gap_models import IntakeSnapshot

    # Create a snapshot where all gaps are open (no satisfying intake/answers)
    snap = IntakeSnapshot(
        business_objective="",
        problem_statement="",
        preferred_cloud="",
        scale_availability="",
        tech_constraints="",
        requirement_texts=[],
        answered_answers={},
    )

    analysis = analyze_gaps(snap)

    # Every code should be in gaps (all unsatisfied)
    gap_codes = [g.code for g in analysis.gaps]
    assert len(gap_codes) == len(
        CODE_ORDER
    ), f"Expected {len(CODE_ORDER)} gaps, got {len(gap_codes)}: {gap_codes}"

    # Gap order must match CODE_ORDER
    assert gap_codes == CODE_ORDER, f"Gaps not in CODE_ORDER. Got: {gap_codes}"


def test_clarification_question_ordering_with_tied_timestamps(client: TestClient, db) -> None:
    """Verify CASE expression provides deterministic ordering when created_at is tied.

    When multiple ClarificationQuestionRow rows are created in the same transaction,
    they receive identical created_at timestamps. Without the CASE expression secondary
    sort, row order is nondeterministic. This test verifies the CASE expression ensures
    CODE_ORDER regardless of insertion order or tied timestamps.
    """
    from datetime import datetime, timezone
    from uuid import uuid4

    from app.db.models import ClarificationQuestionRow, ProjectRow
    from app.modules.requirements.gap_analyze import CODE_ORDER
    from sqlalchemy import text

    # Create a project
    pid = uuid4()
    proj = ProjectRow(
        id=pid,
        name="Test CASE ordering",
        business_objective="test",
        problem_statement="test",
        preferred_cloud="test",
        scale_availability="",
        tech_constraints="",
    )
    db.add(proj)
    db.flush()

    # Insert 10 clarification rows IN REVERSE CODE_ORDER with identical timestamps
    # This tests that the CASE expression can reorder even when insertion order is wrong
    tied_timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    for idx, code in enumerate(reversed(CODE_ORDER)):
        row = ClarificationQuestionRow(
            id=uuid4(),
            project_id=pid,
            code=code,
            prompt=f"Question for {code}",
            category="requirements",
            status="open",
            created_at=tied_timestamp,  # Explicitly tie all timestamps
        )
        db.add(row)
    db.commit()

    # Query with the same order_by used in analyze_interview and get_interview
    from app.modules.requirements.service import _get_code_sort_expression

    rows = (
        db.query(ClarificationQuestionRow)
        .filter(ClarificationQuestionRow.project_id == pid)
        .order_by(ClarificationQuestionRow.created_at.asc(), _get_code_sort_expression().asc())
        .all()
    )

    returned_codes = [r.code for r in rows]

    # Despite being inserted in reverse order with tied timestamps,
    # the CASE expression should return them in CODE_ORDER
    assert (
        returned_codes == CODE_ORDER
    ), f"CASE expression failed to order by CODE_ORDER. Got: {returned_codes}"
