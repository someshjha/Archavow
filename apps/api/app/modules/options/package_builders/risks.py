"""Risk register generation for the package build step."""

from __future__ import annotations

from app.modules.options.generator import OptionTemplate, ProjectContext
from app.modules.options.package_builders._shared import _domain_terms


def build_risks(ctx: ProjectContext, option: OptionTemplate) -> list[dict]:
    terms = _domain_terms(ctx)
    risks: list[dict] = [
        {
            "id": "R-001",
            "title": "Ops load may outrun the team early on",
            "category": "Operations",
            "severity": "high" if option.ops_band in {"high", "very high"} else "medium",
            "likelihood": "medium",
            "impact": (
                f"Ops band reads {option.ops_band}. First incidents can eat the same people "
                "who are still shipping features."
            ),
            "mitigation": (
                "Write the boring runbooks now: golden signals, who gets paged, and a 30-day "
                "hardening list before go-live."
            ),
            "residual_risk": "Medium — until runbooks and on-call are proven in a game day.",
            "owner": "platform",
            "target_date": "before-golive",
        },
        {
            "id": "R-002",
            "title": "Write paths without real auth",
            "category": "Security",
            "severity": "high",
            "likelihood": "medium",
            "impact": terms["write_impact"],
            "mitigation": (
                "Put auth on the gateway and inside services before merge."
            ),
            "residual_risk": "Low if gateway + service auth land; high if deferred.",
            "owner": "security",
            "target_date": "before-golive",
        },
    ]
    stack_l = {s.lower() for s in option.stack}
    if "kafka" in stack_l:
        risks.append(
            {
                "id": "R-003",
                "title": "Kafka failure modes (dupes, lag, poison)",
                "category": "Reliability",
                "severity": "medium",
                "likelihood": "medium",
                "impact": "Events get lost, duplicated, or stuck when brokers or consumers wobble.",
                "mitigation": "acks + retries, idempotent producers, DLQ, and lag alerts on the critical groups.",
                "residual_risk": "Medium — broker incidents still possible under partition/ACL mistakes.",
                "owner": "platform",
                "target_date": "before-golive",
            }
        )
    if any("rto" in r.lower() or "rpo" in r.lower() for r in ctx.requirements) or any(
        k in (ctx.scale_availability or "").lower() for k in ("rto", "rpo")
    ):
        risks.append(
            {
                "id": "R-004",
                "title": "DR numbers on paper, unproven in this region design",
                "category": "Reliability",
                "severity": "high",
                "likelihood": "medium",
                "impact": "Stated RTO/RPO won't hold if we never drill failover or restore.",
                "mitigation": "Write the failover runbook and schedule a restore/failover game day before prod.",
                "residual_risk": "Medium until a successful drill is evidenced.",
                "owner": "platform",
                "target_date": "before-golive",
            }
        )
    else:
        risks.append(
            {
                "id": "R-004",
                "title": "No numeric RTO/RPO yet",
                "category": "Reliability",
                "severity": "medium",
                "likelihood": "high",
                "impact": "Hard to argue the DR design when targets are still 'TBD'.",
                "mitigation": "Get RTO/RPO in the interview, then regenerate the package.",
                "residual_risk": "High while targets remain unspecified.",
                "owner": "solution-architect",
                "target_date": "interview",
            }
        )
    return risks
