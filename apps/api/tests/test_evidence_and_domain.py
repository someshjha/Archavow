"""Unit tests for domain-neutral package builders + evidence coverage states."""

from __future__ import annotations

from app.modules.options.generator import OptionTemplate, ProjectContext
from app.modules.options.package_builders import (
    build_quality_score,
    build_risks,
    build_sequence_mermaid,
    build_threats,
)
from app.modules.options.package_builders.quality_score import COVERAGE_STATES


def _opt(**kwargs) -> OptionTemplate:
    base = dict(
        key="rec",
        title="Postgres on Azure",
        summary="Batch processing",
        pros=["a", "b"],
        cons=["c", "d"],
        fit_score=80,
        cost_band="$$",
        ops_band="medium",
        recommended=True,
        stack=["postgres", "azure"],
    )
    base.update(kwargs)
    return OptionTemplate(**base)


def _cov(score: dict, cid: str) -> str:
    return next(c["coverage"] for c in score["categories"] if c["id"] == cid)


def test_risks_and_threats_are_domain_neutral_without_payment_evidence() -> None:
    ctx = ProjectContext(
        name="ETL File Platform",
        business_objective="Process nightly files",
        problem_statement="Batch misses SLAs",
        preferred_cloud="Azure",
        tech_constraints="Spring Batch, Postgres",
        scale_availability="5M rows/file",
    )
    opt = _opt()
    blob = " ".join(str(x) for x in build_risks(ctx, opt) + build_threats(ctx, opt)).lower()
    assert "payment" not in blob
    assert "settlement" not in blob
    assert "partner" not in blob
    seq = build_sequence_mermaid(ctx, opt).lower()
    assert "payment" not in seq
    assert "submit request" in seq or "submit" in seq or "job trigger" in seq or "scheduler" in seq


def test_payment_vocabulary_only_when_evidenced() -> None:
    ctx = ProjectContext(
        name="Payments Hub",
        business_objective="Payment settlement on Azure",
        problem_statement="Settlement disputes",
        requirements=["PCI and PII controls"],
    )
    opt = _opt(stack=["kafka", "postgres"])
    blob = " ".join(str(x) for x in build_threats(ctx, opt)).lower()
    assert "payment" in blob or "settlement" in blob


def test_evidence_checklist_missing_without_interview() -> None:
    ctx = ProjectContext(name="X", business_objective="Y")
    score = build_quality_score(
        ctx, _opt(), completeness_overall=20, evidence_citation_count=0
    )
    assert score["label"] == "evidence_checklist"
    assert score["overall"] in COVERAGE_STATES
    assert score["overall"] in {"missing", "partial"}
    assert "score" not in score["categories"][0]
    assert score["blockers"] or score["missing_evidence"]
    assert "No org or project standards cited" in score["missing_evidence"]


def test_seed_citations_do_not_inflate_governance() -> None:
    ctx = ProjectContext(
        name="X",
        scale_availability="5k events/sec peak",
        requirements=["RTO 15 min", "RPO 1 min", "OIDC auth"],
        tech_constraints="Postgres Kafka",
    )
    low = build_quality_score(
        ctx, _opt(stack=["kafka", "postgres"]), completeness_overall=80, evidence_citation_count=0
    )
    high = build_quality_score(
        ctx,
        _opt(stack=["kafka", "postgres"]),
        completeness_overall=80,
        evidence_citation_count=2,
        org_standards_cited=True,
    )
    assert _cov(low, "governance_compliance") == "missing"
    assert _cov(high, "governance_compliance") in {"evidenced", "verified"}
    assert COVERAGE_STATES.index(high["overall"]) >= COVERAGE_STATES.index(low["overall"])


def test_auth_and_rto_evidence_raises_security_reliability() -> None:
    bare = ProjectContext(name="X")
    rich = ProjectContext(
        name="X",
        scale_availability="5k events/sec · RTO 15 · RPO 1",
        requirements=["OIDC at gateway", "RTO 15 min · RPO 1 min"],
    )
    opt = _opt()
    s_bare = build_quality_score(bare, opt, completeness_overall=50, evidence_citation_count=0)
    s_rich = build_quality_score(rich, opt, completeness_overall=50, evidence_citation_count=0)
    assert COVERAGE_STATES.index(_cov(s_rich, "security")) > COVERAGE_STATES.index(
        _cov(s_bare, "security")
    )
    assert COVERAGE_STATES.index(_cov(s_rich, "reliability")) > COVERAGE_STATES.index(
        _cov(s_bare, "reliability")
    )


def test_open_interview_categories_cap_security_and_reliability() -> None:
    """Keyword evidence cannot claim coverage the interview never established."""
    ctx = ProjectContext(
        name="X",
        scale_availability="5k events/sec · RTO 15 · RPO 1",
        requirements=["OIDC at gateway", "RTO 15 min · RPO 1 min"],
    )
    opt = _opt()
    full = build_quality_score(ctx, opt, completeness_overall=80, evidence_citation_count=0)
    thin = build_quality_score(
        ctx,
        opt,
        completeness_overall=80,
        evidence_citation_count=0,
        completeness_categories={"reliability": 33, "security_compliance": 50},
    )
    assert _cov(thin, "security") == "partial"
    assert _cov(thin, "reliability") == "missing"
    assert COVERAGE_STATES.index(thin["overall"]) <= COVERAGE_STATES.index(full["overall"])
    assert any("Security & compliance" in m for m in thin["missing_evidence"])


def test_keywords_alone_never_reach_verified() -> None:
    ctx = ProjectContext(
        name="X",
        scale_availability="5k events/sec peak",
        requirements=["RTO 15 min", "RPO 1 min", "OIDC auth", "on-call runbook SLO"],
        tech_constraints="Postgres Kafka budget $10k/month owner platform team",
    )
    score = build_quality_score(
        ctx, _opt(stack=["kafka", "postgres"]), completeness_overall=90, evidence_citation_count=2
    )
    for cat in score["categories"]:
        if cat["id"] == "requirements_completeness":
            continue
        assert cat["coverage"] != "verified", cat


def test_interview_floor_can_verify_security() -> None:
    ctx = ProjectContext(
        name="X",
        requirements=["OIDC at gateway"],
    )
    score = build_quality_score(
        ctx,
        _opt(),
        completeness_overall=90,
        evidence_citation_count=0,
        completeness_categories={"security_compliance": 90},
    )
    assert _cov(score, "security") == "verified"


def test_negated_rto_does_not_score_reliability_high() -> None:
    ctx = ProjectContext(
        name="X",
        requirements=["We have no RTO and no RPO defined yet"],
    )
    score = build_quality_score(
        ctx, _opt(), completeness_overall=80, evidence_citation_count=0
    )
    assert _cov(score, "reliability") in {"missing", "partial"}
    assert score["method"] == "intake_keyword_presence"
    assert score["confidence"] in {"low", "medium"}


def test_option_cost_band_does_not_inflate_cost_score() -> None:
    ctx = ProjectContext(name="X", business_objective="Ship a thing")
    cheap = build_quality_score(
        ctx, _opt(cost_band="$", ops_band="low"), completeness_overall=80, evidence_citation_count=0
    )
    pricey = build_quality_score(
        ctx,
        _opt(cost_band="$$$", ops_band="high"),
        completeness_overall=80,
        evidence_citation_count=0,
    )
    assert _cov(cheap, "cost_awareness") == _cov(pricey, "cost_awareness")
    assert _cov(cheap, "operability") == _cov(pricey, "operability")


def test_option_stack_without_context_adds_alignment_missing() -> None:
    ctx = ProjectContext(name="X", business_objective="Batch files")
    score = build_quality_score(
        ctx,
        _opt(stack=["kafka", "postgres"]),
        completeness_overall=80,
        evidence_citation_count=0,
    )
    assert any(
        "alignment" in m.lower() or "option claims" in m.lower() for m in score["missing_evidence"]
    )


def test_bare_rto_token_without_duration_stays_low() -> None:
    ctx = ProjectContext(name="X", requirements=["Need an RTO someday"])
    score = build_quality_score(
        ctx, _opt(), completeness_overall=80, evidence_citation_count=0
    )
    assert _cov(score, "reliability") in {"missing", "partial"}
