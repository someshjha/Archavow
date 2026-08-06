"""Delivery backlog (epics + user stories) generation."""

from __future__ import annotations

from app.modules.options.generator import OptionTemplate, ProjectContext
from app.modules.options.package_builders import build_epics, render_epics_markdown


def _option(**over) -> OptionTemplate:
    base = dict(
        key="event-driven",
        title="Event-driven claims pipeline",
        summary="Queue-backed intake with rules-based adjudication.",
        pros=["Absorbs bursts", "Clear audit trail"],
        cons=["More moving parts", "Needs stream expertise"],
        fit_score=82,
        cost_band="medium",
        ops_band="medium",
        recommended=True,
        stack=["Java", "Kafka", "AKS", "Postgres"],
    )
    base.update(over)
    return OptionTemplate(**base)


def _ctx(requirements: list[str], **over) -> ProjectContext:
    base = dict(
        name="Claims Automation",
        preferred_cloud="Azure",
        tech_constraints="Java 21, Spring Boot, Kafka",
        scale_availability="2k claims/hour peak · 99.9% availability",
        business_objective="Cut claim cycle time from days to minutes.",
        problem_statement="Manual adjudication cannot keep up with volume.",
        requirements=requirements,
        stated_requirements=requirements,
    )
    base.update(over)
    return ProjectContext(**base)


def test_enabler_epic_and_stories_are_baseline_recommendations():
    epics = build_epics(
        _ctx(["Claimants must submit a claim with supporting documents online."]),
        _option(),
    )
    enabler_epic = next(e for e in epics if e["title"] == "Technical enablers")
    assert enabler_epic["origin"] == "baseline_recommendation"
    assert enabler_epic["requirement_refs"] == []
    for story in enabler_epic["stories"]:
        assert story["origin"] == "baseline_recommendation"
        assert story["requirement_refs"] == []
    for epic in epics:
        if epic["title"] == "Technical enablers":
            continue
        assert epic.get("origin") == "evidence_derived"
        for story in epic["stories"]:
            assert story.get("origin") == "evidence_derived"


def test_requirements_group_into_themed_epics():
    epics = build_epics(
        _ctx(
            [
                "Claimants must submit a claim with supporting documents online.",
                "The system must adjudicate straightforward claims automatically.",
                "Adjusters must review claims the rules cannot decide.",
                "Approved claims must trigger a payment to the claimant.",
            ]
        ),
        _option(),
    )
    titles = [e["title"] for e in epics]
    assert "Submission intake" in titles
    assert "Automated decisioning" in titles
    assert "Human review and exceptions" in titles
    assert "Disbursement and settlement" in titles
    # Enablers are always appended last so business epics read first.
    assert titles[-1] == "Technical enablers"


def test_every_business_story_traces_to_a_requirement():
    epics = build_epics(
        _ctx(
            [
                "Claimants must submit a claim online.",
                "Payments must reconcile against the claim record.",
            ]
        ),
        _option(),
    )
    business = [
        s for e in epics for s in e["stories"] if s["type"] == "business"
    ]
    assert business
    for story in business:
        assert story["requirement_refs"], f"{story['id']} has no traceability"
        assert story["title"].startswith("As a ")
        assert len(story["acceptance_criteria"]) >= 2
        for ac in story["acceptance_criteria"]:
            assert ac["given"] and ac["when"] and ac["then"]


def test_business_stories_never_name_the_implementation_language():
    """Language belongs in enablers and ADRs, not in customer-facing stories."""
    epics = build_epics(
        _ctx(["Claimants must submit a claim online with documents."]),
        _option(),
    )
    for epic in epics:
        for story in epic["stories"]:
            if story["type"] != "business":
                continue
            blob = f"{story['title']} {story['need']}".lower()
            assert "java" not in blob
            assert "kafka" not in blob


def test_enabler_story_adopts_the_evidenced_language():
    epics = build_epics(
        _ctx(["Claimants must submit a claim online."]),
        _option(),
    )
    enablers = [s for e in epics for s in e["stories"] if s["type"] == "enabler"]
    assert any("Java" in s["title"] for s in enablers)


def test_enabler_asks_for_a_language_decision_when_none_is_evidenced():
    epics = build_epics(
        _ctx(["Claimants must submit a claim online."], tech_constraints=""),
        _option(stack=["Managed queue", "Postgres"]),
    )
    enablers = [s for e in epics for s in e["stories"] if s["type"] == "enabler"]
    assert any("agree the implementation language" in s["title"] for s in enablers)


def test_story_and_epic_ids_are_unique():
    epics = build_epics(
        _ctx(
            [
                "Claimants submit claims online.",
                "Automatically adjudicate simple claims.",
                "Adjusters review exceptions.",
                "Flag suspicious duplicate claims for investigation.",
                "Notify the customer when claim status changes.",
                "Retain an audit trail for seven years for compliance.",
            ]
        ),
        _option(),
    )
    epic_ids = [e["id"] for e in epics]
    story_ids = [s["id"] for e in epics for s in e["stories"]]
    assert len(epic_ids) == len(set(epic_ids))
    assert len(story_ids) == len(set(story_ids))


def test_story_titles_do_not_paste_the_raw_requirement_in():
    """"As a claimant, I want to claimants must submit…" was the first output.

    The subject and modal have to be consumed, not carried into the goal clause.
    """
    epics = build_epics(
        _ctx(
            [
                "Claimants must submit a claim online with supporting documents.",
                "Claims above 5,000 or with missing evidence must be routed to an adjuster.",
                "The system must validate the policy is active before adjudication.",
                "Operations managers must see claim volume and cycle time daily.",
            ]
        ),
        _option(),
    )
    for epic in epics:
        for story in epic["stories"]:
            title = story["title"]
            assert " I want to must" not in title
            assert "I want to claimants" not in title
            assert "I want to claims" not in title
            # Article agreement: "As a operations manager" reads as a typo.
            assert "As a operations" not in title
            assert "As a investigator" not in title
            assert "As a integration" not in title
            assert "As an claimant" not in title


def test_person_subject_becomes_the_story_actor():
    epics = build_epics(
        _ctx(["Operations managers must see claim volume and cycle time daily."]),
        _option(),
    )
    story = next(s for e in epics for s in e["stories"] if s["type"] == "business")
    assert story["actor"] == "operations manager"
    assert story["title"].startswith("As an operations manager, I want to see")


def test_system_subject_keeps_a_human_actor():
    """"As a system, I want…" is not a user story; the system is what it acts on."""
    epics = build_epics(
        _ctx(["The system must validate the policy is active before adjudication."]),
        _option(),
    )
    story = next(s for e in epics for s in e["stories"] if s["type"] == "business")
    assert "I want the system to validate" in story["title"]
    assert story["actor"] != "system"


def test_audit_requirement_is_not_stolen_by_the_word_review():
    """"…audit trail for seven years for regulatory review" is audit, not review."""
    epics = build_epics(
        _ctx(
            [
                "Adjusters must review claims the rules cannot decide.",
                "Every decision must retain an immutable audit trail for seven years for regulatory review.",
            ]
        ),
        _option(),
    )
    by_ref = {
        ref: epic["title"]
        for epic in epics
        for ref in (epic["requirement_refs"] or [])
    }
    assert by_ref["R-001"] == "Human review and exceptions"
    assert by_ref["R-002"] == "Audit and compliance evidence"


def test_reporting_requirement_is_not_stolen_by_the_word_exception():
    epics = build_epics(
        _ctx(["Operations managers must see claim volume, cycle time, and exception rates daily."]),
        _option(),
    )
    titles = [e["title"] for e in epics]
    assert "Operational reporting" in titles


def test_render_markdown_includes_requirement_index_and_gherkin():
    reqs = ["Claimants submit claims online.", "Adjudicate simple claims automatically."]
    md = render_epics_markdown(build_epics(_ctx(reqs), _option()), requirements=reqs)
    assert "# Delivery backlog — epics and user stories" in md
    assert "## Requirement index" in md
    assert "**R-001**" in md
    assert "- Given " in md
    assert "  - When " in md or "- When " in md
    assert "Then " in md


def test_render_markdown_without_requirements_skips_the_index():
    md = render_epics_markdown(build_epics(_ctx(["Submit claims online."]), _option()))
    assert "## Requirement index" not in md
    assert "Delivery backlog" in md


def test_id_series_are_contiguous_and_start_at_one():
    """Epic, story, and enabler numbers must read straight down the artifact.

    Enablers keep their own EN series, so continuing the US counter into it (the
    old behaviour) left visible gaps in both.
    """
    epics = build_epics(
        _ctx(
            [
                "Claimants must submit a claim with supporting documents online.",
                "The system must adjudicate straightforward claims automatically.",
                "Adjusters must review claims the rules cannot decide.",
                "Approved claims must trigger a payment to the claimant.",
                "Claimants must be able to check the status of a claim.",
            ]
        ),
        _option(),
    )

    assert [e["id"] for e in epics] == [f"E-{i + 1:03d}" for i in range(len(epics))]

    business = [s for e in epics for s in e["stories"] if s["type"] == "business"]
    enablers = [s for e in epics for s in e["stories"] if s["type"] == "enabler"]
    assert [s["id"] for s in business] == [
        f"US-{i + 1:03d}" for i in range(len(business))
    ]
    assert [s["id"] for s in enablers] == [
        f"EN-{i + 1:03d}" for i in range(len(enablers))
    ]

    ids = {s["id"] for s in enablers}
    for story in enablers:
        for dep in story.get("dependencies") or []:
            assert dep in ids, f"{story['id']} depends on missing {dep}"
        assert [ac["id"] for ac in story["acceptance_criteria"]] == [
            f"AC-{i + 1}" for i in range(len(story["acceptance_criteria"]))
        ]

    for story in business:
        assert [ac["id"] for ac in story["acceptance_criteria"]] == [
            f"AC-{i + 1}" for i in range(len(story["acceptance_criteria"]))
        ]


def test_interview_answers_do_not_become_user_stories():
    """Only requirements stated at intake earn a story.

    Interview answers land in `requirements` too, and feeding them in produced
    stories like "As a user, I want to RTO 15 min".
    """
    ctx = _ctx(["Claimants must submit a claim online."])
    ctx.requirements = [
        *ctx.stated_requirements,
        "RTO 15 min · RPO 1 min",
        "Six engineers, two of them senior, plus one SRE at 50%",
    ]

    stories = [s for e in build_epics(ctx, _option()) for s in e["stories"]]
    business = [s for s in stories if s["type"] == "business"]
    assert len(business) == 1
    assert business[0]["requirement_refs"] == ["R-001"]
    assert "RTO 15 min" not in " ".join(s["title"] for s in stories)


def test_articles_follow_pronunciation_not_spelling():
    titles = " ".join(
        s["title"]
        for e in build_epics(
            _ctx(
                [
                    "Users must be able to submit a claim online.",
                    "An auditor must be able to read the decision history.",
                ]
            ),
            _option(),
        )
        for s in e["stories"]
    )
    assert "As a user" in titles
    assert "As an user" not in titles
    assert "an auditor" in titles.lower()


def test_acronyms_keep_their_case_in_story_titles():
    stories = [
        s
        for e in build_epics(
            _ctx(["PDF summaries must be attached to every settled claim."]), _option()
        )
        for s in e["stories"]
    ]
    titles = " ".join(s["title"] for s in stories)
    assert "PDF" in titles
    assert "pDF" not in titles
