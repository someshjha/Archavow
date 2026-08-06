"""Unit tests for evidence-gated threats and HLD assumptions."""

from __future__ import annotations

from app.modules.options.generator import OptionTemplate, ProjectContext
from app.modules.options.package_builders import build_hld_markdown, build_threats


def _opt(**kwargs) -> OptionTemplate:
    base = dict(
        key="t",
        title="T",
        summary="S",
        pros=["a", "b"],
        cons=["c", "d"],
        fit_score=3,
        cost_band="$$",
        ops_band="medium",
        recommended=True,
        stack=["postgres"],
        origin="template",
    )
    base.update(kwargs)
    return OptionTemplate(**base)


def test_threats_omit_cloud_native_assets_without_evidence() -> None:
    ctx = ProjectContext(
        name="Desktop ETL",
        business_objective="Nightly file transform",
        problem_statement="SLA misses",
        tech_constraints="Spring Batch, Postgres",
    )
    threats = build_threats(ctx, _opt(stack=["postgres", "spring-batch"]))
    blob = " ".join(str(t) for t in threats).lower()
    assert "api gateway" not in blob
    assert "container runtime" not in blob or "cluster" not in blob
    assert "broker partition" not in blob
    # Datastore threat is allowed when postgres is evidenced
    assert any("system of record" in t["asset"].lower() for t in threats)


def test_threats_include_kafka_and_k8s_when_stacked() -> None:
    ctx = ProjectContext(name="Events", tech_constraints="Kafka, AKS, API gateway")
    threats = build_threats(
        ctx, _opt(stack=["kafka", "aks", "postgres", "gateway"])
    )
    assets = " ".join(t["asset"].lower() for t in threats)
    assert "message" in assets or "bus" in assets
    assert "container" in assets
    assert "edge" in assets or "api" in assets


def test_hld_lists_assumptions_not_invented_components() -> None:
    ctx = ProjectContext(name="Batch", tech_constraints="Postgres")
    hld = build_hld_markdown(ctx, _opt(stack=["postgres"], origin="template"))
    assert "## Assumptions" in hld
    assert "Component responsibilities" in hld
    assert "Postgres unless otherwise decided" not in hld
    assert "starter template" in hld.lower() or "Starter template" in hld
