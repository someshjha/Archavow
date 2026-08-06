"""Unit tests for MVP package document builders."""

from __future__ import annotations

from app.modules.options.generator import OptionTemplate, ProjectContext
from app.modules.options.package_builders.documents import (
    MVP_CONDITIONAL,
    MVP_MANDATORY,
    build_package_documents,
)


def _ctx() -> ProjectContext:
    return ProjectContext(
        name="Payments",
        business_objective="Cut settlement latency",
        problem_statement="Batch settlement misses SLA under peak",
        preferred_cloud="Azure",
        tech_constraints="Kafka, AKS, Postgres",
        scale_availability="5k/sec · RTO 15m",
        requirements=["Settle same-day", "RTO 15 min · RPO 1 min"],
    )


def _opt() -> OptionTemplate:
    return OptionTemplate(
        key="event_driven",
        title="Event-driven services",
        summary="Services on AKS with Kafka",
        approach="Domain events for settlement fan-out; Postgres SoR.",
        assumptions=["Team can run Kafka"],
        constraints=["Stay on Azure"],
        key_decisions=["Service boundaries"],
        pros=["Scale", "Replay"],
        cons=["Ops cost", "Complexity"],
        fit_score=90,
        cost_band="$$$",
        ops_band="high",
        recommended=True,
        stack=["aks", "kafka", "postgres"],
        origin="ai",
    )


def test_package_documents_include_mvp_mandatory_keys() -> None:
    docs = build_package_documents(
        _ctx(),
        _opt(),
        options=[
            {
                "title": "Event-driven services",
                "summary": "A",
                "pros": ["a", "b"],
                "cons": ["c", "d"],
                "fit_score": 90,
                "cost_band": "$$$",
                "ops_band": "high",
                "recommended": True,
                "selected": True,
                "stack": ["aks", "kafka"],
                "design": {"approach": "events"},
            },
            {
                "title": "Modular monolith",
                "summary": "B",
                "pros": ["a", "b"],
                "cons": ["c", "d"],
                "fit_score": 70,
                "cost_band": "$$",
                "ops_band": "medium",
                "recommended": False,
                "selected": False,
                "stack": ["container-apps"],
                "design": {},
            },
        ],
        backlog=[{"id": "B-001", "title": "Auth", "priority": "P0", "area": "Security"}],
        adrs=[{"id": "ADR-001", "title": "Go with events"}],
        risks=[{"id": "R-001", "mitigation": "Runbooks"}],
        citations=[{"source_class": "org", "citation": "STD-1", "excerpt": "Encrypt at rest"}],
        quality_score={
            "overall": "partial",
            "missing_evidence": ["DR drill"],
            "blockers": [],
            "categories": [],
        },
        hld_markdown="# HLD\n",
        executive_summary="Settle faster with events.",
        open_questions=["Who owns the ledger?"],
        completeness={"overall": 60, "gaps": ["auth_model"]},
        include_conditional=True,
    )
    for key in MVP_MANDATORY:
        assert key in docs, key
        assert docs[key].strip(), key
    for key in MVP_CONDITIONAL:
        assert key in docs, key
    assert "Business objective" in docs["overview"]
    assert "Functional requirements" in docs["requirements"]
    assert "Recommended option" in docs["options_comparison"]
    assert "Migration and deployment" in docs["migration_plan"]
    assert "Operational readiness" in docs["operational_readiness"]
    assert "Architecture review record" in docs["review_record"]
