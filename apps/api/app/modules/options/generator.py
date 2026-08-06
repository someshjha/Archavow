"""Deterministic architecture option templates (S2) — no LLM required."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProjectContext:
    """Immutable snapshot of one project's evidence, built once per request in
    `options/service.py::_context()` and passed by value into the package builders
    below. High fan-out here is expected — it's a query boundary feeding many pure
    transforms, not a shared mutable object."""

    name: str
    preferred_cloud: str = ""
    tech_constraints: str = ""
    scale_availability: str = ""
    business_objective: str = ""
    problem_statement: str = ""
    requirements: list[str] = field(default_factory=list)
    # Requirements the customer stated at intake, in the order they wrote them.
    # Story traceability (R-001…) is positional over this list, so it must not
    # include interview-derived requirements — those are answers about how the
    # system should be built, not statements of what it must do.
    stated_requirements: list[str] = field(default_factory=list)


@dataclass
class OptionTemplate:
    key: str
    title: str
    summary: str
    pros: list[str]
    cons: list[str]
    fit_score: int
    cost_band: str
    ops_band: str
    recommended: bool
    stack: list[str]
    origin: str = "template"  # template | ai
    approach: str = ""
    assumptions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    key_decisions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.pros) < 2:
            raise ValueError(f"{self.key}: every option needs at least 2 pros")
        if len(self.cons) < 2:
            raise ValueError(f"{self.key}: every option needs at least 2 cons")
        if self.origin not in {"template", "ai"}:
            self.origin = "template"

    def design_dict(self) -> dict:
        return {
            "approach": (self.approach or "").strip(),
            "assumptions": [a for a in self.assumptions if str(a).strip()],
            "constraints": [c for c in self.constraints if str(c).strip()],
            "key_decisions": [d for d in self.key_decisions if str(d).strip()],
        }


def _evidenced_cloud_family(ctx: ProjectContext) -> str:
    """Return azure|aws|gcp|onprem|unspecified — never invent a cloud vendor."""
    cloud = (ctx.preferred_cloud or "").strip().lower()
    constraints = (ctx.tech_constraints or "").lower()
    blob = f"{cloud} {constraints}"

    onprem_markers = (
        "on-prem",
        "onprem",
        "on premise",
        "on-premise",
        "bare metal",
        "datacenter",
        "data centre",
        "self-hosted",
        "self hosted",
        "private cloud",
    )
    if cloud in {"on-prem", "onprem", "on premise", "on-premise", "private"} or any(
        m in blob for m in onprem_markers
    ):
        return "onprem"

    if cloud in {"azure", "microsoft azure"}:
        return "azure"
    if cloud in {"aws", "amazon", "amazon web services"}:
        return "aws"
    if cloud in {"gcp", "google", "google cloud"}:
        return "gcp"
    if cloud in {"other", "unspecified", ""}:
        # Constraints may evidence a cloud without preferred_cloud being set
        if "azure" in constraints and "aws" not in constraints and "gcp" not in constraints:
            return "azure"
        if "aws" in constraints and "azure" not in constraints:
            return "aws"
        if ("gcp" in constraints or "google cloud" in constraints) and "azure" not in constraints:
            return "gcp"
        return "unspecified"

    # Custom label — treat as unspecified vendor for template selection
    return "unspecified"


def _display_cloud(ctx: ProjectContext, family: str) -> str:
    raw = (ctx.preferred_cloud or "").strip()
    if raw and raw.lower() not in {"other", "unspecified"}:
        return raw
    return {
        "azure": "Azure",
        "aws": "AWS",
        "gcp": "GCP",
        "onprem": "on-premises",
        "unspecified": "unspecified",
    }.get(family, "unspecified")


def generate_option_templates(ctx: ProjectContext) -> list[OptionTemplate]:
    """Return starter architecture templates (not scored recommendations).

    fit_score values are ordinal ranks for UI ordering only (3 = default pick).
    Empty / on-prem / Other clouds stay vendor-neutral — never invent Azure.
    """
    family = _evidenced_cloud_family(ctx)
    cloud = _display_cloud(ctx, family)
    constraints = (ctx.tech_constraints or "").lower()
    wants_kafka = "kafka" in constraints or "redpanda" in constraints or "event" in constraints
    wants_k8s = (
        "aks" in constraints
        or "eks" in constraints
        or "gke" in constraints
        or "kubernetes" in constraints
        or "k8s" in constraints
    )

    if family == "azure" and (wants_kafka or wants_k8s):
        return [
            OptionTemplate(
                key="event_driven_services",
                title="Event-driven services on AKS",
                summary=(
                    "Decompose around domain events: services on AKS, Kafka (or Event Hubs "
                    "Kafka protocol) for fan-out/replay, Postgres as system of record."
                ),
                approach=(
                    "Split write and async side-effects into services that publish/consume "
                    "domain events. Synchronous APIs stay thin; Kafka carries fan-out and "
                    "replay. Postgres remains authoritative for commands that need ACID."
                ),
                assumptions=[
                    "Peak load and async fan-out justify broker ops cost",
                    "Team can own Kafka topics, consumer groups, and AKS day-two",
                    "Domain boundaries are clear enough to avoid a distributed monolith",
                ],
                constraints=[
                    "Stay on Azure landing zone already named in intake",
                    "Postgres as explicit SoR unless interview overturns it",
                    "Do not invent a second cloud or broker family",
                ],
                key_decisions=[
                    "Service boundaries vs modular monolith",
                    "Kafka vs managed bus for the async path",
                    "Outbox / idempotency pattern for producers",
                ],
                pros=[
                    "Fits event-heavy problems when Kafka/AKS are already constrained",
                    "Room to grow into multi-region / MirrorMaker later",
                    "Postgres stays the explicit system of record",
                ],
                cons=[
                    "Cluster + brokers aren't cheap to run day two",
                    "You need people who know Kafka and Kubernetes",
                    "Slower to first production than a managed bus",
                ],
                fit_score=3,
                cost_band="$$$",
                ops_band="high",
                recommended=True,
                stack=["aks", "kafka", "postgres", "spring-boot"],
                origin="template",
            ),
            OptionTemplate(
                key="modular_monolith_managed",
                title="Modular monolith on Container Apps",
                summary=(
                    "Keep one deployable with modular boundaries; Azure Container Apps + "
                    "Service Bus + Postgres when the problem does not yet need many services."
                ),
                approach=(
                    "Ship a modular monolith with clear module APIs. Use Service Bus for "
                    "light async work. Split modules into services only when interview "
                    "evidence shows independent scale or ownership pressure."
                ),
                assumptions=[
                    "Moderate scale is enough for the first production cut",
                    "A single team owns the deployable for now",
                    "Cold starts / platform limits are acceptable at stated peaks",
                ],
                constraints=[
                    "Prefer managed Azure primitives over self-run brokers",
                    "Preserve module seams so extraction later is possible",
                    "Postgres remains SoR",
                ],
                key_decisions=[
                    "When (if ever) to extract the first service",
                    "Service Bus vs Kafka protocol for async",
                    "Module ownership and packaging boundaries",
                ],
                pros=[
                    "Less day-two grind than AKS + Kafka",
                    "Faster path to something running",
                    "Lower baseline infra bill",
                ],
                cons=[
                    "Won't stretch as far at extreme partition / throughput",
                    "Less control over networking and consumer layout",
                    "Awkward if you already live in Kafka tooling",
                ],
                fit_score=2,
                cost_band="$$",
                ops_band="medium",
                recommended=False,
                stack=["container-apps", "service-bus", "postgres"],
                origin="template",
            ),
            OptionTemplate(
                key="multi_region_active",
                title="Multi-region active topology",
                summary=(
                    "Active-active / warm-standby across regions with geo-replication. "
                    "Only when RTO/RPO and conflict handling are real requirements."
                ),
                approach=(
                    "Run the same service shape in two regions with MirrorMaker (or "
                    "equivalent) and a clear conflict policy. Failover and data ownership "
                    "are designed up front, not bolted on after an outage."
                ),
                assumptions=[
                    "Hard RTO/RPO numbers exist and justify dual-region cost",
                    "Observability and runbooks can cover two sites",
                    "Conflict / dual-write rules are acceptable to the business",
                ],
                constraints=[
                    "Do not claim near-zero RPO without a tested replication path",
                    "Region blast-radius containment is a first-class requirement",
                ],
                key_decisions=[
                    "Active-active vs warm standby",
                    "Conflict resolution for replicated writes",
                    "Traffic steering and DNS/failover ownership",
                ],
                pros=[
                    "Stronger RTO/RPO once replication is proven",
                    "Region blast-radius stays contained",
                    "Active-active consumers are an option",
                ],
                cons=[
                    "Most expensive of the three",
                    "Dual-write and change-management get messy",
                    "Needs mature observability and runbooks",
                ],
                fit_score=1,
                cost_band="$$$$",
                ops_band="very high",
                recommended=False,
                stack=["aks", "kafka", "mirrormaker", "postgres"],
                origin="template",
            ),
        ]

    # Vendor-neutral / AWS / GCP / on-prem — do not invent Azure services
    stack_tag = {
        "azure": "azure",
        "aws": "aws",
        "gcp": "gcp",
        "onprem": "on-premises",
        "unspecified": "cloud-neutral",
    }.get(family, "cloud-neutral")
    if wants_k8s:
        k8s_tag = {"azure": "aks", "aws": "eks", "gcp": "gke"}.get(family, "kubernetes")
    else:
        k8s_tag = None

    baseline_stack = [stack_tag, "postgres"]
    if k8s_tag:
        baseline_stack.insert(1, k8s_tag)
    if wants_kafka:
        baseline_stack.insert(-1, "kafka")

    cloud_phrase = (
        "on-prem / private infra"
        if family == "onprem"
        else (
            "a landing zone we haven't named yet"
            if family == "unspecified"
            else cloud
        )
    )

    return [
        OptionTemplate(
            key="modular_services_baseline",
            title=(
                f"Modular services on {cloud}"
                if family not in {"unspecified", "onprem"}
                else "Cloud-neutral modular services"
            ),
            summary=(
                f"Working draft for {cloud_phrase}: modular services, messaging where needed, "
                "Postgres as SoR. Refine once problem-specific interview answers land."
            ),
            approach=(
                "Carve the problem into a few independently deployable modules with clear "
                "APIs. Use messaging only where fan-out or decoupling is evidenced. Keep "
                "Postgres as the system of record until interview says otherwise."
            ),
            assumptions=[
                "Domain seams are known enough to avoid a distributed monolith",
                "One primary data store is enough for the first cut",
                "Landing zone / runtime choice matches intake constraints",
            ],
            constraints=[
                (
                    f"Stay within the named landing zone ({cloud})"
                    if family not in {"unspecified", "onprem"}
                    else "Stay vendor-neutral until cloud/on-prem is decided"
                ),
                "Do not invent brokers or clouds absent from evidence",
            ],
            key_decisions=[
                "Service vs module boundaries",
                "Sync API vs async messaging for each workflow",
                "System-of-record ownership",
            ],
            pros=[
                (
                    f"Uses the landing zone you named ({cloud})"
                    if family not in {"unspecified", "onprem"}
                    else "Stays vendor-neutral until cloud/on-prem is decided"
                ),
                "Keeps the first cut small with managed or standard pieces",
                "Postgres is a boring, known SoR when you need one",
            ],
            cons=[
                "May need hardening for peak or multi-region load",
                "Not specialized for streaming-first work",
                "Messaging and store choices still need real ADRs",
            ],
            fit_score=3,
            cost_band="$$$",
            ops_band="medium",
            recommended=True,
            stack=baseline_stack,
            origin="template",
        ),
        OptionTemplate(
            key="modular_monolith_serverless",
            title="Modular monolith, serverless-leaning",
            summary=(
                "One deployable with module seams; managed serverless (or lightest "
                "equivalent) to keep ops quiet until scale pressure is proven."
            ),
            approach=(
                "Implement the problem as a modular monolith behind managed compute. "
                "Extract services only when interview evidence shows independent scale, "
                "failure domains, or team ownership."
            ),
            assumptions=[
                "Cold starts / platform limits are acceptable at stated peaks",
                "A single team can own the deployable initially",
                "Long-running work is limited or can be offloaded later",
            ],
            constraints=[
                "Prefer managed primitives over self-run clusters",
                "Preserve module seams for later extraction",
            ],
            key_decisions=[
                "Extraction triggers (scale, ownership, failure isolation)",
                "Where async work lives if peaks grow",
            ],
            pros=[
                "Lower ongoing ops burden",
                "Pay-for-use where the platform allows it",
                "Smaller team can experiment faster",
            ],
            cons=[
                "Cold starts and platform limits at peak",
                "Less control over networking and tenancy",
                "Long-running work can get awkward",
            ],
            fit_score=2,
            cost_band="$$",
            ops_band="low",
            recommended=False,
            stack=[stack_tag, "serverless"],
            origin="template",
        ),
        OptionTemplate(
            key="multi_site_resilience",
            title="Multi-site / multi-region",
            summary=(
                "Active-active or warm-standby across sites/regions. "
                "Only adopt after RTO/RPO and conflict handling are real."
            ),
            approach=(
                "Duplicate the working shape across sites with an explicit failover and "
                "conflict policy. Resilience is a topology choice, not a bigger single cluster."
            ),
            assumptions=[
                "Hard RTO/RPO numbers exist and justify dual-site cost",
                "Runbooks and drills can cover more than one site",
            ],
            constraints=[
                "Do not claim DR targets without a tested path",
                "Blast radius stays in one site/region by design",
            ],
            key_decisions=[
                "Active-active vs warm standby",
                "Replication and conflict handling",
                "Traffic steering ownership",
            ],
            pros=[
                "Stronger RTO/RPO once replication is proven",
                "Blast radius stays in one site/region",
                "Better fit for always-on / regulated workloads",
            ],
            cons=[
                "Costs more and moves more parts",
                "Replication conflict is a real design problem",
                "Runbooks and drills get heavier",
            ],
            fit_score=1,
            cost_band="$$$$",
            ops_band="high",
            recommended=False,
            stack=[stack_tag, "multi-region"],
            origin="template",
        ),
    ]
