"""Implementation backlog generation for the package build step."""

from __future__ import annotations

from app.modules.options.generator import OptionTemplate, ProjectContext
from app.modules.options.package_builders._shared import _k8s_runtime


def build_backlog(ctx: ProjectContext, option: OptionTemplate) -> list[dict]:
    stack_l = {s.lower() for s in option.stack}
    items = [
        {
            "id": "B-001",
            "title": "Auth on every write path (gateway + service)",
            "priority": "P0",
            "area": "Security",
            "notes": "Gateway and service auth before merge.",
            "acceptance_criteria": [
                "No anonymous write routes in gateway or services",
                "Authz covered on write paths (tests or security review)",
            ],
            "dependencies": [],
            "item_type": "enabler",
        },
        {
            "id": "B-002",
            "title": "Golden signals, dashboards, and who gets paged",
            "priority": "P0",
            "area": "Operability",
            "notes": f"{option.title} sits at ops band {option.ops_band} — don't wing on-call.",
            "acceptance_criteria": [
                "Dashboards for latency/errors/saturation exist",
                "On-call roster and severity defs documented",
            ],
            "dependencies": ["B-001"],
            "item_type": "enabler",
        },
        {
            "id": "B-003",
            "title": "Failover / restore game day for the stated RTO/RPO",
            "priority": "P1",
            "area": "Reliability",
            "notes": ctx.scale_availability or "If numbers are missing, grab them in the interview first.",
            "acceptance_criteria": [
                "Restore/failover drill completed with notes",
                "RTO/RPO evidence attached to package or Knowledge",
            ],
            "dependencies": ["B-002"],
            "item_type": "spike",
        },
        {
            "id": "B-004",
            "title": "Export the package and walk ADRs with the people who care",
            "priority": "P1",
            "area": "Governance",
            "notes": "The export zip is the review packet — no slide rebuild needed.",
            "acceptance_criteria": [
                "Handoff ZIP downloaded",
                "Review record has named reviewers or scheduled review",
            ],
            "dependencies": [],
            "item_type": "enabler",
        },
    ]
    if "kafka" in stack_l:
        items.append(
            {
                "id": "B-005",
                "title": "Topic design: partitions, retention, DLQ, consumer groups",
                "priority": "P0",
                "area": "Integration",
                "notes": "Match the org Kafka checklist if one is in Knowledge.",
                "acceptance_criteria": [
                    "Topics, retention, DLQ, and ACLs documented",
                    "Idempotent producer pattern agreed",
                ],
                "dependencies": ["B-001"],
                "item_type": "enabler",
            }
        )
    if "aks" in stack_l or "eks" in stack_l or "gke" in stack_l or "kubernetes" in stack_l or "k8s" in stack_l:
        runtime = _k8s_runtime(ctx, stack_l)
        product = runtime.get("product") or "Kubernetes"
        items.append(
            {
                "id": "B-006",
                "title": f"{product} hygiene: network policy, HPA, non-root, secrets",
                "priority": "P1",
                "area": "Platform",
                "notes": "Use the org K8s baseline checklist as a quick gate.",
                "acceptance_criteria": [
                    "Non-root + network policy on critical workloads",
                    "Secrets not baked into images",
                ],
                "dependencies": ["B-002"],
                "item_type": "enabler",
            }
        )
    return items
