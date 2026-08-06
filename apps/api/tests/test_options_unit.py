"""Unit tests for deterministic architecture option templates."""

from __future__ import annotations

from app.modules.options.generator import ProjectContext, generate_option_templates


def test_azure_kafka_stack_yields_three_options() -> None:
    ctx = ProjectContext(
        name="Payments",
        preferred_cloud="Azure",
        tech_constraints="Spring Boot, Kafka, AKS",
        scale_availability="5k events/sec",
        requirements=["RTO 15 min · RPO 1 min"],
    )
    options = generate_option_templates(ctx)
    assert len(options) == 3
    assert sum(1 for o in options if o.recommended) == 1
    assert all(o.pros and o.cons for o in options)
    assert any("Kafka" in o.title or "AKS" in o.title or "Event-driven" in o.title for o in options)
    assert all(o.approach and o.assumptions and o.constraints and o.key_decisions for o in options)


def test_every_option_has_labeled_pros_and_cons() -> None:
    for ctx in (
        ProjectContext(name="A", preferred_cloud="Azure", tech_constraints="Kafka, AKS"),
        ProjectContext(name="B", preferred_cloud="AWS", tech_constraints="containers"),
    ):
        for opt in generate_option_templates(ctx):
            assert len(opt.pros) >= 2, opt.key
            assert len(opt.cons) >= 2, opt.key
            assert all(p.strip() for p in opt.pros)
            assert all(c.strip() for c in opt.cons)


def test_templates_are_labelled_not_scored_recommendations() -> None:
    ctx = ProjectContext(name="Underspecified", preferred_cloud="Azure")
    options = generate_option_templates(ctx)
    assert all(o.origin == "template" for o in options)
    assert all(
        "working draft" in o.summary.lower()
        or "draft" in o.summary.lower()
        or "template" in o.origin
        for o in options
    )
    assert "aligned to stated constraints" not in " ".join(o.summary for o in options).lower()
    # Ordinal ranks only (not /100 recommendation theatre)
    assert all(1 <= o.fit_score <= 3 for o in options)


def test_empty_cloud_does_not_invent_azure() -> None:
    ctx = ProjectContext(
        name="Underspecified",
        preferred_cloud="",
        tech_constraints="Kubernetes, Postgres",
    )
    options = generate_option_templates(ctx)
    blob = " ".join(
        f"{o.title} {o.summary} {' '.join(o.stack)}" for o in options
    ).lower()
    assert "aks" not in blob.split()  # word-level; "peaks" must not trip this
    assert "container-apps" not in blob
    assert "service-bus" not in blob
    assert "azure" not in blob.split()
    assert any("cloud-neutral" in o.stack or "kubernetes" in o.stack for o in options)


def test_onprem_stays_vendor_neutral() -> None:
    ctx = ProjectContext(
        name="Plant floor",
        preferred_cloud="On-prem",
        tech_constraints="Kubernetes, Kafka",
    )
    options = generate_option_templates(ctx)
    blob = " ".join(f"{o.title} {' '.join(o.stack)}" for o in options).lower()
    assert "aks" not in blob
    assert "eks" not in blob
    assert any("on-premises" in o.stack for o in options)

