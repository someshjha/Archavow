"""Unit tests for deterministic gap detection (no network / no LLM)."""

from __future__ import annotations

from app.modules.requirements.gaps import (
    IntakeSnapshot,
    analyze_gaps,
    answer_satisfies,
    is_placeholder_answer,
    kind_from_category,
)


def test_sparse_intake_flags_rto_rpo_and_residency() -> None:
    snap = IntakeSnapshot(
        business_objective="Modernize APIs",
        problem_statement="Slow batch",
        preferred_cloud="Azure",
        scale_availability="",
        tech_constraints="Spring Boot",
        requirement_texts=[],
    )
    result = analyze_gaps(snap)
    codes = {g.code for g in result.gaps}
    assert "rto_rpo" in codes
    assert "data_residency" in codes
    assert "peak_traffic" in codes
    assert result.completeness.overall < 70


def test_answered_rto_removes_gap() -> None:
    snap = IntakeSnapshot(
        business_objective="Payments on AKS",
        problem_statement="Need event platform",
        preferred_cloud="Azure",
        scale_availability="5k events/sec peak · 99.9%",
        tech_constraints="Kafka, AKS",
        requirement_texts=["RTO 15 min · RPO 1 min"],
        answered_answers={"rto_rpo": "RTO 15 min · RPO 1 min"},
    )
    result = analyze_gaps(snap)
    codes = {g.code for g in result.gaps}
    assert "rto_rpo" not in codes
    assert "peak_traffic" not in codes
    assert "rto_rpo" in result.captured or any("RTO" in c for c in result.captured)


def test_placeholder_scale_does_not_satisfy_peak_traffic() -> None:
    for placeholder in ("TBD", "unknown", "not discussed", "standard scale", "high", "N/A"):
        snap = IntakeSnapshot(
            preferred_cloud="AWS",
            scale_availability=placeholder,
            tech_constraints="Python",
        )
        result = analyze_gaps(snap)
        assert "peak_traffic" in {g.code for g in result.gaps}, placeholder


def test_quantified_scale_satisfies_peak_traffic() -> None:
    snap = IntakeSnapshot(
        preferred_cloud="Azure",
        scale_availability="1k rps",
    )
    result = analyze_gaps(snap)
    assert "peak_traffic" not in {g.code for g in result.gaps}


def test_placeholder_interview_answer_does_not_close_peak_gap() -> None:
    snap = IntakeSnapshot(
        preferred_cloud="AWS",
        scale_availability="",
        answered_answers={"peak_traffic": "TBD"},
    )
    result = analyze_gaps(snap)
    assert "peak_traffic" in {g.code for g in result.gaps}
    assert "peak_traffic" not in snap.answered_codes


def test_placeholder_interview_answer_does_not_close_rto_gap() -> None:
    snap = IntakeSnapshot(
        preferred_cloud="Azure",
        answered_answers={"rto_rpo": "unknown"},
    )
    result = analyze_gaps(snap)
    assert "rto_rpo" in {g.code for g in result.gaps}


def test_valid_peak_interview_answer_closes_gap() -> None:
    snap = IntakeSnapshot(
        preferred_cloud="Azure",
        answered_answers={"peak_traffic": "Peak 5k events/sec sustained"},
    )
    result = analyze_gaps(snap)
    assert "peak_traffic" not in {g.code for g in result.gaps}


def test_kind_from_category_mapping() -> None:
    assert kind_from_category("requirements") == "fr"
    assert kind_from_category("nfrs") == "nfr"
    assert kind_from_category("security") == "security"
    assert kind_from_category("other") == "other"


def test_analyze_gaps_uses_neutral_stub_prompts() -> None:
    from app.modules.requirements.gap_analyze import analyze_gaps, stub_prompt

    snap = IntakeSnapshot(business_objective="Cut claim cycle time")
    result = analyze_gaps(snap)
    assert result.gaps
    for gap in result.gaps:
        assert gap.prompt.startswith("Clarify:"), gap.prompt
        assert "OAuth" not in gap.prompt
        assert "mTLS" not in gap.prompt
        assert "manual process" not in gap.prompt.lower()
    assert stub_prompt("auth_model") == "Clarify: auth model."

    from app.modules.requirements.answer_checks import SUGGESTION_TEMPLATES, suggestion_template

    snap = IntakeSnapshot(preferred_cloud="Azure")
    banned = ("60%", "10 minute", "2-4", "2–4", "100 request", "4 hour", "15 minute", "oauth2", "mtls")
    for code in SUGGESTION_TEMPLATES:
        text = suggestion_template(code, snap) or ""
        low = text.lower()
        for token in banned:
            assert token not in low, f"{code} invents {token!r}: {text}"


def test_matches_suggestion_template_detects_verbatim() -> None:
    from app.modules.requirements.answer_checks import (
        matches_suggestion_template,
        suggestion_template,
    )

    snap = IntakeSnapshot()
    draft = suggestion_template("rto_rpo", snap)
    assert draft
    assert matches_suggestion_template("rto_rpo", draft, snap)
    assert matches_suggestion_template("rto_rpo", f"  {draft}  ", snap)
    assert not matches_suggestion_template("rto_rpo", "RTO 15 min · RPO 1 min", snap)

    assert answer_satisfies("auth_model", "OIDC via Entra ID")
    assert not answer_satisfies("auth_model", "TBD")
    assert not answer_satisfies("auth_model", "jwt")
    assert not answer_satisfies("auth_model", "OIDC")
    assert answer_satisfies("cloud", "AWS us-east-1 and us-west-2")
    assert not answer_satisfies("cloud", "region")
    assert not answer_satisfies("cloud", "AWS")
    assert not is_placeholder_answer("AWS us-east-1")
    assert is_placeholder_answer("TBD")


def test_bare_keywords_do_not_close_consistency_or_rto() -> None:
    assert not answer_satisfies("consistency", "postgres")
    assert not answer_satisfies("consistency", "database")
    assert not answer_satisfies("consistency", "kafka")
    assert answer_satisfies("consistency", "Postgres is the system of record")
    assert not answer_satisfies("rto_rpo", "RTO")
    assert not answer_satisfies("rto_rpo", "RTO and RPO discussed")
    assert answer_satisfies("rto_rpo", "RTO 15 min · RPO 1 min")


def test_intake_bare_keywords_do_not_bypass_validators() -> None:
    """Intake must not close gaps via loose blob keyword scans."""
    snap = IntakeSnapshot(
        business_objective="Need RTO planning and OIDC eventually",
        problem_statement="consistency and database concerns",
        preferred_cloud="Azure",
        scale_availability="high",
        tech_constraints="jwt, postgres, kafka",
        requirement_texts=["GDPR", "region"],
    )
    result = analyze_gaps(snap)
    codes = {g.code for g in result.gaps}
    assert "rto_rpo" in codes
    assert "peak_traffic" in codes
    assert "auth_model" in codes
    assert "consistency" in codes
    assert "cloud" in codes  # bare preferred_cloud provider is insufficient
    assert "data_residency" in codes


def test_intake_substantive_scale_closes_peak_and_rto() -> None:
    snap = IntakeSnapshot(
        preferred_cloud="Azure eastus",
        scale_availability="5k events/sec peak · RTO 15 min · RPO 1 min",
        requirement_texts=["Postgres is the system of record"],
    )
    result = analyze_gaps(snap)
    codes = {g.code for g in result.gaps}
    assert "peak_traffic" not in codes
    assert "rto_rpo" not in codes
    assert "consistency" not in codes
    assert "cloud" not in codes


def test_split_intake_rto_rpo_across_fields_closes_gap() -> None:
    snap = IntakeSnapshot(
        preferred_cloud="Azure eastus",
        scale_availability="RTO 15 minutes",
        requirement_texts=["RPO 1 minute for payment ledger"],
    )
    result = analyze_gaps(snap)
    assert "rto_rpo" not in {g.code for g in result.gaps}

    assert is_placeholder_answer("OIDC via Entra ID — TBD for partners")
    assert is_placeholder_answer("AWS us-east-1 (to be decided)")
    assert is_placeholder_answer("Postgres is the system of record, pending")
    assert is_placeholder_answer("Peak 5k events/sec — unknown for burst")
    assert not is_placeholder_answer("OIDC via Entra ID for partners")
    assert not answer_satisfies("auth_model", "OIDC authentication pending")
    assert not answer_satisfies("cloud", "AWS region TBD later")
    assert not answer_satisfies("consistency", "system of record to be defined")
    assert not answer_satisfies("rto_rpo", "RTO 15 min · RPO 1 min TBD")
