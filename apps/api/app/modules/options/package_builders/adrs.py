"""ADR generation for the package build step."""

from __future__ import annotations

from app.modules.options.generator import OptionTemplate, ProjectContext
from app.modules.options.package_builders._shared import _k8s_runtime


def build_adrs(ctx: ProjectContext, option: OptionTemplate) -> list[dict]:
    stack_csv = ", ".join(option.stack) or "the selected stack"
    cloud = ctx.preferred_cloud or "an undecided landing zone"
    constraints = ctx.tech_constraints or "nothing firm yet"
    scale = ctx.scale_availability or "scale still open"
    problem = (ctx.problem_statement or ctx.business_objective or "").strip()
    context_bits = [
        f"{ctx.name} is aiming at {cloud}. Constraints on the table: “{constraints}”.",
        f"Scale note: “{scale}”.",
    ]
    if problem:
        context_bits.append(f"Problem in scope: “{problem[:280]}”.")
    if (option.approach or "").strip():
        context_bits.append(f"Chosen approach: {option.approach.strip()[:320]}")

    alternatives = [
        a for a in (option.key_decisions or [])[:2]
    ]
    # Always record that other scored options were available at generate time
    alternatives = [
        "Other scored architecture options generated for this project (see options comparison)",
        *alternatives,
    ]

    adrs: list[dict] = [
        {
            "id": "ADR-001",
            "title": f"Go with {option.title}",
            "status": "accepted",
            "context": " ".join(context_bits),
            "decision": (
                f"We'll take **{option.title}** ({stack_csv}) as the working shape. "
                f"Rough cost {option.cost_band}, ops load {option.ops_band}."
            ),
            "rationale": (
                (option.approach or option.summary).strip()
                or "Selected as the packaged option after human gate."
            ),
            "alternatives": alternatives,
            "consequences": [
                *option.pros[:2],
                *[f"Trade-off: {c}" for c in option.cons[:2]],
                *[f"Assumption: {a}" for a in (option.assumptions or [])[:2]],
            ],
            "owner": "solution-architect",
        }
    ]
    stack_l = {s.lower() for s in option.stack}
    next_id = 2
    if "kafka" in stack_l or "event" in (ctx.tech_constraints or "").lower():
        adrs.append(
            {
                "id": f"ADR-{next_id:03d}",
                "title": "Kafka (or Kafka-protocol) for the async path",
                "status": "accepted",
                "context": (
                    "We need fan-out and replay more than a simple request/response loop. "
                    "Interview cited peak load and async fan-out as the reason for messaging."
                ),
                "decision": (
                    "Put Kafka (or Event Hubs in Kafka mode) on the async path; keep Postgres "
                    "as the system of record. Wire client security to whatever Kafka standard "
                    "the org already has (see citations if we found one)."
                ),
                "rationale": "Replay, multiple consumers, and peak fan-out outweigh managed-bus simplicity here.",
                "alternatives": [
                    "Managed bus / queue only (Service Bus, SQS, Pub/Sub)",
                    "Synchronous fan-out without a broker",
                ],
                "consequences": [
                    "Replay and multiple consumers become straightforward",
                    "Someone has to own brokers, topics, and ACLs",
                    "Producers need idempotency; consumers need a clear offset story",
                ],
                "owner": "platform",
            }
        )
        next_id += 1
    if (
        "aks" in stack_l
        or "eks" in stack_l
        or "gke" in stack_l
        or "kubernetes" in stack_l
        or "k8s" in stack_l
    ):
        runtime = _k8s_runtime(ctx, stack_l)
        adrs.append(
            {
                "id": f"ADR-{next_id:03d}",
                "title": f"Run services on {runtime['title']}",
                "status": "proposed",
                "context": runtime["context"],
                "decision": runtime["decision"],
                "rationale": "Container orchestration matches stated constraints and scale ambitions.",
                "alternatives": [
                    "Managed serverless / container apps without a full cluster",
                    "VMs / classic PaaS without Kubernetes",
                ],
                "consequences": [
                    "Day-2 cluster work is real — upgrades, RBAC, node pools",
                    "Multi-AZ later is doable if we don't paint ourselves into a corner",
                    "Platform (or whoever wears that hat) owns the control plane lifecycle",
                ],
                "owner": "platform",
            }
        )
        next_id += 1
    for decision in (option.key_decisions or [])[:4]:
        adrs.append(
            {
                "id": f"ADR-{next_id:03d}",
                "title": decision[:120],
                "status": "proposed",
                "context": (
                    f"Contested choice called out while packing **{option.title}** "
                    f"for {ctx.name}."
                ),
                "decision": decision,
                "rationale": "Surfaced as a key decision on the selected option; needs explicit acceptance.",
                "alternatives": ["Defer until interview evidence is stronger", "Reject and keep simpler path"],
                "consequences": [
                    "Needs explicit owner and acceptance criteria",
                    "Revisit if intake or interview answers change",
                ],
                "owner": "solution-architect",
            }
        )
        next_id += 1
    return adrs
