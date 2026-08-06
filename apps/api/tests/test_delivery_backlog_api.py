"""Requirements intake → package epics → export, end to end over HTTP."""

from __future__ import annotations

from fastapi.testclient import TestClient

_REQUIREMENTS = [
    "Claimants must submit a claim online with supporting documents.",
    "The system must adjudicate straightforward claims automatically.",
    "Adjusters must review claims the rules cannot decide.",
    "Approved claims must trigger a payment to the claimant.",
    "Every decision must retain an audit trail for compliance.",
]


def _project(client: TestClient) -> str:
    res = client.post(
        "/api/v1/projects",
        json={
            "name": "Claims Automation",
            "business_objective": "Cut claim cycle time from days to minutes.",
            "problem_statement": "Manual adjudication cannot keep up with claim volume.",
            "preferred_cloud": "Azure",
            "scale_availability": "2k claims/hour peak · 99.9% availability · RTO 15m",
            "tech_constraints": "Java 21, Spring Boot, Kafka, Postgres, Entra ID",
            "stack_tags": ["azure", "java", "kafka"],
            "requirements": _REQUIREMENTS,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["data"]["id"]


def _package(client: TestClient, pid: str) -> dict:
    gen = client.post(f"/api/v1/projects/{pid}/options/generate")
    assert gen.status_code in (200, 201), gen.text
    options = client.get(f"/api/v1/projects/{pid}/options").json()["data"]["options"]
    chosen = next((o for o in options if o.get("recommended")), options[0])
    sel = client.post(f"/api/v1/projects/{pid}/options/{chosen['id']}/select")
    assert sel.status_code in (200, 201), sel.text
    built = client.post(f"/api/v1/projects/{pid}/package/generate")
    assert built.status_code in (200, 201), built.text
    return built.json()["data"]


def test_intake_requirements_are_persisted_and_returned(client: TestClient) -> None:
    pid = _project(client)
    got = client.get(f"/api/v1/projects/{pid}")
    assert got.status_code == 200
    assert got.json()["data"]["requirements"] == _REQUIREMENTS


def test_intake_requirements_feed_the_requirements_list(client: TestClient) -> None:
    pid = _project(client)
    res = client.get(f"/api/v1/projects/{pid}/requirements")
    assert res.status_code == 200, res.text
    texts = [r["text"] for r in res.json()["data"]]
    for requirement in _REQUIREMENTS:
        assert requirement in texts


def test_updating_intake_replaces_requirements_without_duplicating(
    client: TestClient,
) -> None:
    pid = _project(client)
    res = client.put(
        f"/api/v1/projects/{pid}/intake",
        json={"requirements": ["Claimants must submit a claim online."]},
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["requirements"] == [
        "Claimants must submit a claim online."
    ]


def test_package_exposes_epics_with_traceable_stories(client: TestClient) -> None:
    pid = _project(client)
    pkg = _package(client, pid)
    epics = pkg["epics"]
    assert epics, "package should carry a delivery backlog"

    titles = [e["title"] for e in epics]
    assert "Technical enablers" in titles

    business = [s for e in epics for s in e["stories"] if s["type"] == "business"]
    assert business
    for story in business:
        assert story["requirement_refs"]
        assert story["acceptance_criteria"]

    enablers = [s for e in epics for s in e["stories"] if s["type"] == "enabler"]
    assert enablers


def test_export_includes_epics_and_stories_document(client: TestClient) -> None:
    pid = _project(client)
    _package(client, pid)
    res = client.post(f"/api/v1/projects/{pid}/exports", json={"layout": "folder"})
    assert res.status_code in (200, 201), res.text
    files = {f["path"]: f["content"] for f in res.json()["data"]["files"]}
    assert "backlog/epics-and-stories.md" in files
    content = files["backlog/epics-and-stories.md"]
    assert "Requirement index" in content
    assert "R-001" in content
    assert "Given " in content
    assert "backlog/epics-and-stories.md" in files["README.md"]


def test_package_without_requirements_has_enablers_only(client: TestClient) -> None:
    res = client.post(
        "/api/v1/projects",
        json={
            "name": "Sparse project",
            "business_objective": "Modernise the platform.",
            "preferred_cloud": "AWS",
        },
    )
    pid = res.json()["data"]["id"]
    pkg = _package(client, pid)
    # No stated requirements means no business epics to trace — only enablers.
    assert [e["title"] for e in pkg["epics"]] == []
