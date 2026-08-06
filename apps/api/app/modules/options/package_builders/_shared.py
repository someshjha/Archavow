"""Shared helpers used across the package builders — evidence-gated vocabulary and Mermaid label plumbing."""

from __future__ import annotations

from app.modules.options.generator import OptionTemplate, ProjectContext


def _context_blob(ctx: ProjectContext) -> str:
    return " ".join(
        [
            ctx.name,
            ctx.business_objective,
            ctx.problem_statement,
            ctx.scale_availability,
            ctx.tech_constraints,
            *ctx.requirements,
        ]
    ).lower()


def _domain_terms(ctx: ProjectContext) -> dict[str, str]:
    """Vocabulary gated on evidence in the project context — never invent domain facts."""
    blob = _context_blob(ctx)
    has_payment = any(k in blob for k in ("payment", "pay ", "settlement", "ledger"))
    has_pii = any(k in blob for k in ("pii", "personal data", "gdpr", "phi", "hipaa"))
    has_partner = any(k in blob for k in ("partner", "b2b", "external client"))
    has_event = any(k in blob for k in ("event", "kafka", "stream", "pubsub", "message"))

    submit = "Submit payment request" if has_payment else (
        "Submit event" if has_event else "Submit request"
    )
    caller = "a partner" if has_partner else "an unauthenticated caller"
    forged = "forged payment events" if has_payment else (
        "forged events" if has_event else "forged requests"
    )
    state = "payment state" if has_payment else "authoritative state"
    disclose = (
        "Payloads with PII land on topics readable by broad consumer groups."
        if has_pii
        else "Sensitive payloads land on channels readable by overly broad consumer groups."
    )
    repudiation = (
        "Producer denies publishing a payment event after a settlement dispute."
        if has_payment
        else "Producer denies publishing a message after a dispute."
    )
    write_impact = (
        "Unauthenticated or over-privileged APIs can corrupt payment or event write paths."
        if has_payment
        else "Unauthenticated or over-privileged APIs can corrupt write paths."
    )
    clients = "Clients / partners" if has_partner else "Clients"
    return {
        "submit": submit,
        "caller": caller,
        "forged": forged,
        "state": state,
        "disclose": disclose,
        "repudiation": repudiation,
        "write_impact": write_impact,
        "clients": clients,
    }


def _stack_flags(ctx: ProjectContext, option: OptionTemplate) -> dict[str, bool]:
    stack_l = {s.lower() for s in option.stack}
    blob = _context_blob(ctx) + " " + " ".join(stack_l)
    # problem_statement conventionally describes existing pain being replaced
    # ("batch jobs miss SLAs") rather than the target shape, so it's excluded
    # here to avoid reading legacy-pain language as evidence for the new design.
    forward_blob = (
        " ".join(
            [
                ctx.name,
                ctx.business_objective,
                ctx.scale_availability,
                ctx.tech_constraints,
                *ctx.requirements,
            ]
        ).lower()
        + " "
        + " ".join(stack_l)
    )
    return {
        "api_edge": any(
            k in blob for k in ("gateway", "ingress", "api", "rest", "http", "bff")
        ),
        "datastore": any(
            k in blob for k in ("postgres", "sql", "cosmos", "database", "store", "redis")
        ),
        "messaging": any(
            k in blob
            for k in (
                "kafka",
                "service-bus",
                "message bus",
                "messaging",
                "event-hub",
                "event hub",
                "pubsub",
                "pub/sub",
                "queue",
                "sqs",
                "sns",
            )
        ),
        "containers": any(
            k in blob
            for k in ("aks", "kubernetes", "k8s", "container", "docker", "pod")
        ),
        "serverless": any(k in blob for k in ("serverless", "container-apps", "functions", "lambda")),
        "spring": any(k in blob for k in ("spring", "java")),
        "batch": any(k in forward_blob for k in ("batch", "etl", "job", "worker")),
    }


def _runtime_label(flags: dict[str, bool], stack: set[str]) -> str:
    if flags["spring"] and flags["containers"]:
        return "Spring Boot on containers"
    if flags["spring"]:
        return "Spring Boot"
    if flags["batch"]:
        return "Batch / worker"
    if flags["containers"]:
        return "Container workloads"
    if flags["serverless"]:
        return "Serverless / functions"
    for token in sorted(stack):
        if token and token not in {"api", "rest", "http"}:
            return token.replace("-", " ").title()[:40]
    return "Application service"


def _db_label(stack: set[str]) -> str:
    if "postgres" in stack or "postgresql" in stack:
        return "Postgres"
    if "cosmos" in stack:
        return "Cosmos DB"
    if "redis" in stack:
        return "Redis"
    if any("sql" in s for s in stack):
        return "SQL database"
    return "System of record"


def _bus_label(stack: set[str]) -> str:
    if "kafka" in stack:
        return "Kafka"
    if "event-hubs" in stack or "event_hubs" in stack or "event-hub" in stack:
        return "Event Hubs"
    if "service-bus" in stack:
        return "Service Bus"
    if "pubsub" in stack:
        return "Pub/Sub"
    return "Message bus"


def _mmd_id(text: str, *, fallback: str = "System", limit: int = 24) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in (text or ""))[:limit]
    return safe or fallback


def _mmd_label(text: str, *, limit: int = 80) -> str:
    """Escape a Mermaid/C4 quoted label."""
    cleaned = (
        (text or "")
        .replace("\n", " ")
        .replace('"', "'")
        .replace("—", "-")
        .replace("·", "-")
        .strip()
    )
    return cleaned[:limit]


def _k8s_runtime(ctx: ProjectContext, stack_l: set[str]) -> dict[str, str]:
    """Pick EKS/AKS/GKE from evidenced cloud — never invent a cloud footprint."""
    cloud = (ctx.preferred_cloud or "").strip().lower()
    blob = " ".join(
        [
            cloud,
            ctx.tech_constraints or "",
            *stack_l,
            _context_blob(ctx),
        ]
    ).lower()

    def _pack(title: str, footprint: str, product: str) -> dict[str, str]:
        return {
            "title": title,
            "product": product,
            "context": (
                f"We're containerizing services and {footprint} is the landing zone "
                "we actually named. Portable orchestration beats one-off VMs here."
            ),
            "decision": (
                f"Run the app pods on {product}. Start with boring defaults: ingress, HPA, "
                "and network policies. Fancy mesh later if we need it."
            ),
        }

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
        return {
            "title": "Kubernetes (on-premises)",
            "product": "Kubernetes",
            "context": (
                "This isn't a public-cloud managed offer — the footprint is on-prem / private. "
                "We still want portable containers without inventing a DIY orchestrator."
            ),
            "decision": (
                "Run services on Kubernetes we operate (or the private platform team operates). "
                "Same basics: ingress, HPA, network policy. Keep control-plane ownership explicit."
            ),
        }

    if "eks" in stack_l or cloud in {"aws", "amazon", "amazon web services"}:
        return _pack("EKS / Kubernetes", "AWS", "EKS")
    if "gke" in stack_l or cloud in {"gcp", "google", "google cloud"}:
        return _pack("GKE / Kubernetes", "GCP", "GKE")
    if "aks" in stack_l or cloud in {"azure", "microsoft azure"}:
        return _pack("AKS / Kubernetes", "Azure", "AKS")
    if "aws" in blob and "azure" not in blob and "gcp" not in blob:
        return _pack("EKS / Kubernetes", "AWS", "EKS")
    if ("gcp" in blob or "google cloud" in blob) and "azure" not in blob and "aws" not in blob:
        return _pack("GKE / Kubernetes", "GCP", "GKE")
    if "azure" in blob:
        return _pack("AKS / Kubernetes", "Azure", "AKS")
    return {
        "title": "Kubernetes",
        "product": "Kubernetes",
        "context": (
            "Containers are in play, but we haven't locked EKS vs AKS vs GKE (or on-prem). "
            "Don't bake a vendor name into the design until that lands."
        ),
        "decision": (
            "Design for plain Kubernetes: ingress, HPA, network policies. Pick the managed "
            "flavor (or on-prem) once the environment is decided."
        ),
    }
