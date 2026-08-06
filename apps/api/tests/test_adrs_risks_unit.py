"""Unit tests for ADR + risk builders."""

from __future__ import annotations

from app.modules.options.generator import OptionTemplate, ProjectContext
from app.modules.options.package_builders import (
    build_adrs,
    build_backlog,
    build_risks,
)


def _ctx_opt() -> tuple[ProjectContext, OptionTemplate]:
    ctx = ProjectContext(
        name="AKS Event Platform",
        preferred_cloud="Azure",
        tech_constraints="Spring Boot, Kafka, AKS",
        scale_availability="5k/sec · 99.9%",
        requirements=["RTO 15 min · RPO 1 min"],
    )
    opt = OptionTemplate(
        key="recommended_streaming",
        title="AKS + Kafka + Postgres",
        summary="Streaming platform",
        pros=["a", "b"],
        cons=["c", "d"],
        fit_score=86,
        cost_band="$$$",
        ops_band="high",
        recommended=True,
        stack=["aks", "kafka", "postgres"],
    )
    return ctx, opt


def test_build_adrs_includes_stack_decision() -> None:
    ctx, opt = _ctx_opt()
    adrs = build_adrs(ctx, opt)
    assert len(adrs) >= 1
    joined = " ".join(a["decision"] for a in adrs).lower()
    assert "kafka" in joined or "aks" in joined


def test_build_adrs_aws_kubernetes_uses_eks_not_aks() -> None:
    ctx = ProjectContext(
        name="Orders platform",
        preferred_cloud="AWS",
        tech_constraints="Kubernetes, Postgres",
        scale_availability="99.9%",
        requirements=[],
    )
    opt = OptionTemplate(
        key="k8s",
        title="EKS services",
        summary="Container platform",
        pros=["a", "b"],
        cons=["c", "d"],
        fit_score=80,
        cost_band="$$",
        ops_band="medium",
        recommended=True,
        stack=["kubernetes", "postgres"],
    )
    adrs = build_adrs(ctx, opt)
    k8s = next(a for a in adrs if "Run services on" in a["title"] or "EKS" in a["title"])
    blob = f"{k8s['title']} {k8s['context']} {k8s['decision']}".lower()
    assert "eks" in blob
    assert "aks" not in blob
    assert "azure" not in blob


def test_build_adrs_includes_key_decisions() -> None:
    ctx, opt = _ctx_opt()
    opt.key_decisions = ["Own the outbox pattern", "Split billing module first"]
    adrs = build_adrs(ctx, opt)
    titles = " ".join(a["title"] for a in adrs)
    assert "Own the outbox pattern" in titles
    assert "Split billing module first" in titles


def test_build_backlog_aws_kubernetes_uses_eks_not_aks() -> None:
    ctx = ProjectContext(
        name="Orders platform",
        preferred_cloud="AWS",
        tech_constraints="Kubernetes",
    )
    opt = OptionTemplate(
        key="k8s",
        title="EKS services",
        summary="Container platform",
        pros=["a", "b"],
        cons=["c", "d"],
        fit_score=80,
        cost_band="$$",
        ops_band="medium",
        recommended=True,
        stack=["kubernetes", "postgres"],
    )
    backlog = build_backlog(ctx, opt)
    k8s_items = [b for b in backlog if b["id"] == "B-006"]
    assert k8s_items
    assert "EKS" in k8s_items[0]["title"]
    assert "AKS" not in k8s_items[0]["title"]


def test_build_risks_covers_ops_and_security() -> None:
    ctx, opt = _ctx_opt()
    risks = build_risks(ctx, opt)
    cats = {r["category"] for r in risks}
    assert "Reliability" in cats or "Security" in cats or "Operations" in cats
    assert all(r["mitigation"] for r in risks)
    # Context has no payment evidence — must stay domain-neutral
    blob = " ".join(str(r) for r in risks).lower()
    assert "payment" not in blob
    assert "settlement" not in blob
