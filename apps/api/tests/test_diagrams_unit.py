"""Unit tests for sequence/deploy Mermaid builders."""

from __future__ import annotations

from app.modules.options.generator import (
    OptionTemplate,
    ProjectContext,
)
from app.modules.options.package_builders import (
    build_deploy_mermaid,
    build_sequence_mermaid,
)


def _opt() -> tuple[ProjectContext, OptionTemplate]:
    ctx = ProjectContext(
        name="AKS Event Platform",
        preferred_cloud="Azure",
        tech_constraints="Spring Boot, Kafka, AKS",
    )
    opt = OptionTemplate(
        key="rec",
        title="AKS + Kafka + Postgres",
        summary="Streaming",
        pros=["a", "b"],
        cons=["c", "d"],
        fit_score=86,
        cost_band="$$$",
        ops_band="high",
        recommended=True,
        stack=["aks", "kafka", "postgres", "spring-boot"],
    )
    return ctx, opt


def test_sequence_has_kafka_path() -> None:
    ctx, opt = _opt()
    mmd = build_sequence_mermaid(ctx, opt)
    assert mmd.startswith("sequenceDiagram")
    assert "Kafka" in mmd or "kafka" in mmd.lower()


def test_deploy_has_cluster_nodes() -> None:
    ctx, opt = _opt()
    mmd = build_deploy_mermaid(ctx, opt)
    assert "flowchart" in mmd or mmd.startswith("graph ")
    assert "AKS" in mmd or "aks" in mmd.lower() or "Cluster" in mmd


def test_c4_container_uses_mermaid11_queue_alias() -> None:
    from app.modules.options.package_builders import build_c4_container_mermaid

    ctx, opt = _opt()
    mmd = build_c4_container_mermaid(ctx, opt)
    assert "ContainerQueue" in mmd
    assert "Container_Queue" not in mmd
    assert "—" not in mmd


def test_c4_context_models_the_target_system_not_archavow() -> None:
    """The Context diagram must show the system-under-design's real actors,
    not a meta-narrative about an architect using Archavow."""
    from app.modules.options.package_builders import build_c4_mermaid

    ctx, opt = _opt()
    mmd = build_c4_mermaid(ctx, opt)
    assert "Archavow" not in mmd
    assert "Architect / operator" not in mmd
    assert "Designs / reviews" not in mmd


def test_deploy_not_misclassified_as_batch_by_legacy_pain_language() -> None:
    """A problem_statement describing legacy batch/job pain (the thing being
    replaced) must not make the *target* deployment diagram look like a
    scheduled batch worker when the stack evidences a messaging-driven system."""
    from app.modules.options.package_builders import build_deploy_mermaid

    ctx = ProjectContext(
        name="AKS Event Platform",
        preferred_cloud="Azure",
        tech_constraints="Spring Boot, Kafka, AKS",
        business_objective="Ingest events reliably with clear disaster-recovery targets.",
        problem_statement="Batch jobs miss SLAs at peak load; need an event-driven path.",
    )
    opt = OptionTemplate(
        key="rec",
        title="AKS + Kafka",
        summary="Streaming",
        pros=["a", "b"],
        cons=["c", "d"],
        fit_score=86,
        cost_band="$$$",
        ops_band="high",
        recommended=True,
        stack=["aks", "kafka", "spring-boot"],
    )
    mmd = build_deploy_mermaid(ctx, opt)
    assert "Scheduler / trigger" not in mmd
    assert "Client" in mmd


def test_c4_context_is_level1_with_labeled_rels() -> None:
    from app.modules.options.package_builders import build_c4_mermaid

    ctx, opt = _opt()
    mmd = build_c4_mermaid(ctx, opt)
    assert "Level 1 Context" in mmd
    assert 'Rel(user' in mmd


def test_c4_container_has_nested_boundaries() -> None:
    from app.modules.options.package_builders import build_c4_container_mermaid

    ctx, opt = _opt()
    mmd = build_c4_container_mermaid(ctx, opt)
    assert "Boundary(frontend" in mmd or "Front end" in mmd
    assert "Boundary(backend" in mmd or "Backend" in mmd


def test_component_and_dataflow_builders() -> None:
    from app.modules.options.package_builders import (
        build_c4_component_mermaid,
        build_dataflow_mermaid,
    )

    ctx, opt = _opt()
    comp = build_c4_component_mermaid(ctx, opt)
    assert comp.startswith("C4Component")
    assert "Component(domain" in comp
    flow = build_dataflow_mermaid(ctx, opt)
    assert flow.startswith("flowchart TB")
    assert "starts the request" in flow
    assert "Authoritative write" in flow
    assert "Domain events" in flow
    assert "Kafka" in flow or "kafka" in flow.lower()
    assert "<br" not in flow.lower()
    # No nested cloud topology — that lived on the removed deployment diagram.
    assert "Private network" not in flow
    assert "VPC" not in flow
    assert "AKS cluster" not in flow


def test_dataflow_always_describes_nodes_without_store_evidence() -> None:
    from app.modules.options.package_builders import build_dataflow_mermaid

    ctx = ProjectContext(
        name="Claims Intake",
        business_objective="Adjudicate claims without rekeying",
        problem_statement="Adjusters rekey every claim from email",
        preferred_cloud="Azure",
    )
    opt = OptionTemplate(
        key="simple",
        title="Managed API",
        summary="Light API",
        pros=["a", "b"],
        cons=["c", "d"],
        fit_score=70,
        cost_band="$$",
        ops_band="low",
        recommended=True,
        stack=["api"],
    )
    flow = build_dataflow_mermaid(ctx, opt)
    assert "Claim payload" in flow
    assert "Persist outcome" in flow or "System of record" in flow
    assert "Insufficient evidence" not in flow
