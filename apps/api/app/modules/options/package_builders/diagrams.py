"""C4 and data-flow Mermaid builders — nested boundaries, labeled relations, evidence-gated."""

from __future__ import annotations

from app.modules.options.generator import OptionTemplate, ProjectContext
from app.modules.options.package_builders._shared import (
    _bus_label,
    _context_blob,
    _db_label,
    _domain_terms,
    _mmd_id,
    _mmd_label,
    _runtime_label,
    _stack_flags,
)


def _system_description(ctx: ProjectContext, option: OptionTemplate) -> str:
    bits = [
        (option.approach or option.summary or "").strip(),
        (ctx.business_objective or "").strip(),
    ]
    text = next((b for b in bits if b), "System under design")
    return _mmd_label(text, limit=90)


def _external_systems(ctx: ProjectContext, option: OptionTemplate) -> list[tuple[str, str, str]]:
    """Return (id, name, desc) for external systems evidenced in context — never invent."""
    blob = _context_blob(ctx) + " " + " ".join(s.lower() for s in option.stack)
    out: list[tuple[str, str, str]] = []
    cloud = (ctx.preferred_cloud or "").strip()
    if cloud and cloud.lower() not in {"other", "unspecified"}:
        out.append(("landing", _mmd_label(cloud, limit=32), "Landing zone / platform"))
    if any(k in blob for k in ("mainframe", "legacy core", "core banking")):
        out.append(("legacy", "Legacy core system", "Existing system of record"))
    if any(k in blob for k in ("email", "smtp", "notification", "ses", "sendgrid")):
        out.append(("notify", "Notification service", "Email / push notifications"))
    if any(k in blob for k in ("partner", "b2b", "external api", "third-party", "third party")):
        out.append(("partner", "Partner / external API", "Upstream or downstream integration"))
    if any(k in blob for k in ("idp", "okta", "auth0", "entra", "cognito", "sso", "oidc")):
        out.append(("idp", "Identity provider", "SSO / OIDC"))
    return out[:5]


def build_c4_mermaid(ctx: ProjectContext, option: OptionTemplate) -> str:
    """Level 1 — System Context: users, system under design, external systems."""
    safe = _mmd_id(ctx.name)
    title = _mmd_label(f"Level 1 Context - {ctx.name}", limit=64)
    sys_name = _mmd_label(ctx.name or option.title, limit=48)
    summary = _system_description(ctx, option)
    clients = _mmd_label(_domain_terms(ctx)["clients"], limit=40)
    externals = _external_systems(ctx, option)

    lines = [
        "C4Context",
        f"    title {title}",
        f'    Person(user, "{clients}", "Primary users of the system")',
        f'    System({safe}, "{sys_name}", "{summary}")',
        f'    Rel(user, {safe}, "Uses", "HTTPS")',
    ]
    for eid, name, desc in externals:
        lines.append(f'    System_Ext({eid}, "{name}", "{_mmd_label(desc, limit=48)}")')
        if eid == "landing":
            lines.append(f'    Rel({safe}, {eid}, "Runs on", "Managed platform")')
        elif eid == "idp":
            lines.append(f'    Rel({safe}, {eid}, "Authenticates via", "OIDC / SAML")')
        elif eid == "notify":
            lines.append(f'    Rel({safe}, {eid}, "Sends notifications using", "API")')
        elif eid == "legacy":
            lines.append(f'    Rel({safe}, {eid}, "Reads / writes", "Integration")')
        else:
            lines.append(f'    Rel({safe}, {eid}, "Integrates with", "API")')

    if not any(e[0] == "landing" for e in externals):
        cloud = _mmd_label(ctx.preferred_cloud or "Hosting platform", limit=40)
        lines.append(f'    System_Ext(cloud, "{cloud}", "Hosting (unspecified vendor)")')
        lines.append(f'    Rel({safe}, cloud, "Runs on")')

    return "\n".join(lines) + "\n"


def build_c4_container_mermaid(ctx: ProjectContext, option: OptionTemplate) -> str:
    """Level 2 — Containers with nested Front end / Backend / Data boundaries."""
    flags = _stack_flags(ctx, option)
    stack = {s.lower() for s in option.stack}
    boundary = _mmd_id(ctx.name, limit=20)
    title = _mmd_label(f"Level 2 Containers - {ctx.name}", limit=64)
    sys_name = _mmd_label(ctx.name or option.title, limit=48)
    runtime = _mmd_label(_runtime_label(flags, stack), limit=40)
    batch_only = flags["batch"] and not flags["api_edge"]
    clients = _mmd_label(_domain_terms(ctx)["clients"], limit=40)
    externals = _external_systems(ctx, option)

    lines = [
        "C4Container",
        f"    title {title}",
    ]

    if batch_only:
        lines.append(
            '    System_Ext(trigger, "Scheduler / trigger", '
            '"Cron, file drop, queue, or operator")'
        )
    else:
        lines.append(f'    Person(user, "{clients}", "Primary users")')

    for eid, name, desc in externals:
        if eid == "landing":
            continue
        lines.append(f'    System_Ext({eid}, "{name}", "{_mmd_label(desc, limit=48)}")')

    lines.append(f'    System_Boundary({boundary}, "{sys_name}") {{')

    # Front end / edge
    if flags["api_edge"] or not batch_only:
        lines.append('        Boundary(frontend, "Front end / edge") {')
        if flags["api_edge"]:
            lines.append(
                '            Container(gw, "API Gateway", "Ingress", '
                '"Authn, rate limits, routing")'
            )
        if not batch_only:
            lines.append(
                '            Container(client_ux, "Client channel", "Web / API clients", '
                '"User-facing entry")'
            )
        lines.append("        }")

    # Backend
    lines.append('        Boundary(backend, "Backend") {')
    app_name = "Batch worker" if batch_only else "Application services"
    app_desc = (
        "Job processing and domain workflows"
        if batch_only
        else "Domain logic and orchestration"
    )
    lines.append(
        f'            Container(app, "{app_name}", "{runtime}", "{app_desc}")'
    )
    if flags["messaging"]:
        bus_tech = _mmd_label(_bus_label(stack), limit=40)
        lines.append(
            f'            ContainerQueue(bus, "Event / message bus", "{bus_tech}", '
            '"Async fan-out and replay")'
        )
    lines.append("        }")

    # Data
    if flags["datastore"]:
        db_tech = _mmd_label(_db_label(stack), limit=40)
        lines.append('        Boundary(data, "Data") {')
        lines.append(
            f'            ContainerDb(db, "System of record", "{db_tech}", '
            '"Authoritative state")'
        )
        lines.append("        }")

    lines.append("    }")

    # Relations — numbered semantics via descriptive labels (sequence diagram has autonumber)
    if batch_only:
        lines.append('    Rel(trigger, app, "1 Starts job", "Schedule / event")')
    elif flags["api_edge"]:
        lines.append('    Rel(user, client_ux, "1 Uses", "HTTPS")')
        lines.append('    Rel(client_ux, gw, "2 Calls API", "HTTPS / JWT")')
        lines.append('    Rel(gw, app, "3 Routes", "mTLS or private link")')
    else:
        lines.append('    Rel(user, app, "1 Invokes", "HTTPS")')

    step = 4 if flags["api_edge"] else 2
    if flags["datastore"]:
        lines.append(f'    Rel(app, db, "{step} Reads/writes", "SQL / SDK")')
        step += 1
    if flags["messaging"]:
        lines.append(f'    Rel(app, bus, "{step} Publishes events", "Async")')
        step += 1

    for eid, _name, _desc in externals:
        if eid == "landing":
            continue
        if eid == "idp" and flags["api_edge"]:
            lines.append(f'    Rel(gw, {eid}, "{step} Validates tokens", "OIDC")')
        elif eid == "legacy":
            lines.append(f'    Rel(app, {eid}, "{step} Integrates", "API / adapter")')
        elif eid == "notify":
            lines.append(f'    Rel(app, {eid}, "{step} Notifies", "API")')
        elif eid == "partner":
            lines.append(f'    Rel(app, {eid}, "{step} Exchanges", "API")')
        step += 1

    landing = next((e for e in externals if e[0] == "landing"), None)
    if landing:
        lines.append(
            f'    System_Ext(landing, "{landing[1]}", "{_mmd_label(landing[2], limit=40)}")'
        )
        lines.append('    Rel(app, landing, "Runs on", "Managed compute")')

    return "\n".join(lines) + "\n"


def build_c4_component_mermaid(ctx: ProjectContext, option: OptionTemplate) -> str:
    """Level 3 — Components inside the application container."""
    flags = _stack_flags(ctx, option)
    stack = {s.lower() for s in option.stack}
    title = _mmd_label(f"Level 3 Components - {ctx.name}", limit=64)
    runtime = _mmd_label(_runtime_label(flags, stack), limit=40)

    lines = [
        "C4Component",
        f"    title {title}",
        f'    Container_Boundary(app, "Application services ({runtime})") {{',
        '        Component(api, "API / controllers", "Interface", "Inbound commands and queries")',
        '        Component(domain, "Domain services", "Application", "Business rules and workflows")',
        '        Component(security, "Security component", "Cross-cutting", "Authn/z checks")',
    ]
    if flags["messaging"]:
        lines.append(
            '        Component(publisher, "Event publisher", "Integration", '
            '"Outbox / idempotent produce")'
        )
        lines.append(
            '        Component(consumer, "Event consumers", "Integration", '
            '"Handlers and DLQ path")'
        )
    if flags["datastore"]:
        lines.append(
            '        Component(repo, "Persistence adapter", "Data", '
            '"Maps domain to system of record")'
        )
    if any(k in _context_blob(ctx) for k in ("partner", "legacy", "mainframe", "external")):
        lines.append(
            '        Component(facade, "Integration facade", "Adapter", '
            '"Shields domain from external systems")'
        )
    lines.append("    }")

    if flags["api_edge"]:
        lines.append('    Container_Ext(gw, "API Gateway", "Ingress")')
        lines.append('    Rel(gw, api, "Forwards authenticated requests")')
    lines.append('    Rel(api, security, "Authorizes")')
    lines.append('    Rel(api, domain, "Delegates")')
    if flags["datastore"]:
        lines.append('    Rel(domain, repo, "Loads / stores")')
        db = _mmd_label(_db_label(stack), limit=32)
        lines.append(f'    ContainerDb_Ext(db, "{db}", "SQL", "System of record")')
        lines.append('    Rel(repo, db, "SQL / SDK")')
    if flags["messaging"]:
        bus = _mmd_label(_bus_label(stack), limit=32)
        lines.append('    Rel(domain, publisher, "Emits domain events")')
        lines.append(f'    Container_Ext(bus, "{bus}", "Event bus", "Async fan-out")')
        lines.append('    Rel(publisher, bus, "Publish")')
        lines.append('    Rel(bus, consumer, "Deliver")')
        lines.append('    Rel(consumer, domain, "Apply side effects")')

    return "\n".join(lines) + "\n"


def build_sequence_mermaid(ctx: ProjectContext, option: OptionTemplate) -> str:
    """Key interaction sequence — numbered steps, auth, persist, async path."""
    flags = _stack_flags(ctx, option)
    stack = {s.lower() for s in option.stack}
    terms = _domain_terms(ctx)
    submit = _mmd_label(terms["submit"], limit=40)
    note = _mmd_label(f"{ctx.name} - {option.title}", limit=80)
    batch_only = flags["batch"] and not flags["api_edge"]

    lines = [
        "sequenceDiagram",
        "    autonumber",
        f"    %% {note}",
    ]
    if batch_only:
        lines.append("    participant Trigger as SchedulerOrTrigger")
        lines.append("    participant App as ApplicationServices")
    else:
        lines.append("    actor Client")
        if flags["api_edge"]:
            lines.append("    participant GW as APIGateway")
            if any(
                k in _context_blob(ctx)
                for k in ("idp", "okta", "auth0", "entra", "cognito", "sso", "oidc")
            ):
                lines.append("    participant IdP as IdentityProvider")
        lines.append("    participant App as ApplicationServices")

    if flags["datastore"]:
        lines.append(f"    participant DB as {_mmd_label(_db_label(stack), limit=24)}")
    if flags["messaging"]:
        lines.append(f"    participant Bus as {_mmd_label(_bus_label(stack), limit=24)}")
        lines.append("    participant Worker as AsyncConsumer")

    if batch_only:
        lines.append("    Trigger->>App: Fire job (schedule / file / queue)")
        lines.append(
            "    Note over Trigger,App: Trigger mechanism unresolved until evidenced"
        )
    elif flags["api_edge"]:
        lines.append(f"    Client->>GW: {submit}")
        if any(
            k in _context_blob(ctx)
            for k in ("idp", "okta", "auth0", "entra", "cognito", "sso", "oidc")
        ):
            lines.append("    GW->>IdP: Validate token")
            lines.append("    IdP-->>GW: Claims")
        lines.append("    GW->>App: Forward authorized request")
    else:
        lines.append(f"    Client->>App: {submit}")

    lines.append("    App->>App: Apply domain rules")
    if flags["datastore"]:
        lines.append("    App->>DB: Persist authoritative state")
        lines.append("    DB-->>App: Ack")
    if flags["messaging"]:
        lines.append("    App->>Bus: Publish domain event")
        lines.append("    Bus-->>App: Ack")
        lines.append("    Bus->>Worker: Deliver event")
        lines.append("    Worker->>Worker: Side effects / projections")
        if flags["datastore"]:
            lines.append("    Worker->>DB: Update derived state (if any)")

    if batch_only:
        lines.append("    App-->>Trigger: Job result / status")
    elif flags["api_edge"]:
        lines.append("    App-->>GW: Response")
        lines.append("    GW-->>Client: Response")
    else:
        lines.append("    App-->>Client: Response")

    lines.append(
        f"    Note over App: {note}"
    )
    return "\n".join(lines) + "\n"


def build_deploy_mermaid(ctx: ProjectContext, option: OptionTemplate) -> str:
    """Deployment / infrastructure — nested region → network → runtime like cloud reference diagrams."""
    flags = _stack_flags(ctx, option)
    stack = {s.lower() for s in option.stack}
    cloud_label = _mmd_label(ctx.preferred_cloud or "Landing zone", limit=32)
    clients = _mmd_label(_domain_terms(ctx)["clients"], limit=36)
    runtime = _mmd_label(_runtime_label(flags, stack), limit=36)
    batch_only = flags["batch"] and not flags["api_edge"]
    k8s_name = "Cluster"
    cloud_l = (ctx.preferred_cloud or "").lower()
    if flags["containers"]:
        if "aks" in stack or "azure" in cloud_l:
            k8s_name = "AKS cluster"
        elif "eks" in stack or "aws" in cloud_l:
            k8s_name = "EKS cluster"
        elif "gke" in stack or "gcp" in cloud_l:
            k8s_name = "GKE cluster"
        else:
            k8s_name = "Kubernetes cluster"

    lines = [
        "flowchart TB",
        "    classDef boundary fill:#fffdf8,stroke:#c45c26,stroke-width:1.5px,stroke-dasharray: 4 3",
        "    classDef runtime fill:#e8efe9,stroke:#2f5d50,stroke-width:1.5px",
        "    classDef data fill:#eef2f7,stroke:#3d5a80,stroke-width:1.5px",
        "    classDef edge fill:#f7efe6,stroke:#c45c26,stroke-width:1.5px",
        f'    Users(["1 {clients}"])',
        f'    subgraph Region["{cloud_label} region"]',
        "    direction TB",
        '    subgraph Net["Private network / VPC"]',
        "    direction TB",
    ]

    if flags["containers"]:
        lines.append(f'    subgraph Cluster["{k8s_name}"]')
        lines.append("    direction LR")
        if flags["api_edge"]:
            lines.append('    Ing["2 Ingress / Gateway"]:::edge')
            lines.append(f'    App["3 {runtime}"]:::runtime')
            lines.append("    Ing --> App")
        else:
            lines.append(f'    App["2 {runtime}"]:::runtime')
        lines.append("    end")
        app_node = "App"
        ingress_node = "Ing" if flags["api_edge"] else "App"
    elif flags["serverless"]:
        lines.append('    App["2 Managed compute / serverless"]:::runtime')
        app_node = "App"
        ingress_node = "App"
    else:
        lines.append(f'    App["2 {runtime}"]:::runtime')
        app_node = "App"
        ingress_node = "App"

    step = 4 if flags["containers"] and flags["api_edge"] else 3
    if flags["messaging"]:
        bus = _mmd_label(_bus_label(stack), limit=28)
        lines.append(f'    Bus["{step} {bus}"]:::data')
        lines.append(f"    {app_node} --> Bus")
        step += 1
    if flags["datastore"]:
        db = _mmd_label(_db_label(stack), limit=28)
        lines.append(f'    DB[("{step} {db}")]:::data')
        lines.append(f"    {app_node} --> DB")
        step += 1

    lines.append("    end")  # Net
    lines.append(f'    Obs["{step} Observability / logs / metrics"]:::edge')
    lines.append(f"    {app_node} -.-> Obs")
    lines.append("    end")  # Region

    lines.append(f"    Users --> {ingress_node}" if not batch_only else f"    Trigger[Scheduler / trigger] --> {ingress_node}")
    lines.append("    class Region,Net boundary")
    if flags["containers"]:
        lines.append("    class Cluster boundary")
    return "\n".join(lines) + "\n"


def build_dataflow_mermaid(ctx: ProjectContext, option: OptionTemplate) -> str:
    """How data moves through the selected option — top-to-bottom, labeled steps.

    Node labels stay single-line: the web Mermaid renderer uses htmlLabels=false
    and strips foreignObject, so <br/> / multi-line HTML never shows up in the UI.
    Descriptions live in the node title and on the edges instead.
    """
    flags = _stack_flags(ctx, option)
    stack = {s.lower() for s in option.stack}
    blob = _context_blob(ctx)
    sensitive = any(
        k in blob for k in ("pii", "phi", "payment", "gdpr", "hipaa", "secret", "claim")
    )
    clients = _mmd_label(_domain_terms(ctx)["clients"], limit=28)
    runtime = _mmd_label(_runtime_label(flags, stack), limit=32)
    payload = _mmd_label(_payload_name(ctx, sensitive=sensitive), limit=32)
    protocol = "HTTPS" if flags["api_edge"] or not flags["batch"] else "Scheduled job"

    lines = [
        "flowchart TB",
        "    classDef actor fill:#eef2f7,stroke:#3d5a80,stroke-width:1.5px",
        "    classDef edge fill:#f7efe6,stroke:#c45c26,stroke-width:1.5px",
        "    classDef app fill:#e8efe9,stroke:#2f5d50,stroke-width:1.5px",
        "    classDef data fill:#eef2f7,stroke:#3d5a80,stroke-width:1.5px",
        f'    Clients(["1 {clients} - starts the request"]):::actor',
    ]

    if flags["api_edge"] or not flags["batch"]:
        lines.append(
            '    Edge["2 API gateway - auth, authorize, rate-limit"]:::edge'
        )
        lines.append(f'    Clients -->|"{protocol}: {payload}"| Edge')
        lines.append(
            f'    App["3 {runtime} - business rules"]:::app'
        )
        lines.append('    Edge -->|"Authorized command"| App')
        step = 4
    else:
        lines.append(
            f'    App["2 {runtime} - batch / worker processing"]:::app'
        )
        lines.append('    Clients -->|"Trigger / schedule"| App')
        step = 3

    if flags["datastore"]:
        db = _mmd_label(_db_label(stack), limit=24)
        lines.append(
            f'    DB[("{step} {db} - system of record")]:::data'
        )
        lines.append('    App -->|"Authoritative write"| DB')
        lines.append('    DB -->|"Read models / queries"| App')
        step += 1
    else:
        lines.append(
            f'    State["{step} App state - name the SoR in interview"]:::data'
        )
        lines.append('    App -->|"Persist outcome"| State')
        step += 1

    if flags["messaging"]:
        bus = _mmd_label(_bus_label(stack), limit=24)
        lines.append(
            f'    Bus["{step} {bus} - async domain events"]:::data'
        )
        lines.append('    App -->|"Domain events"| Bus')
        step += 1
        lines.append(
            f'    Consumers["{step} Downstream - payments, audit, notify"]:::app'
        )
        lines.append('    Bus -->|"Fan-out"| Consumers')
        step += 1

    if sensitive:
        lines.append(
            f'    Guard["{step} Data controls - ACL, retention, no secrets in logs"]:::edge'
        )
        lines.append('    App -.->|"PII / secrets stay scoped"| Guard')
        if flags["messaging"]:
            lines.append('    Bus -.->|"Topic ACL + retention"| Guard')

    return "\n".join(lines) + "\n"


def _payload_name(ctx: ProjectContext, *, sensitive: bool) -> str:
    """Human label for what travels on the wire — domain first, not generic 'data'."""
    blob = _context_blob(ctx).lower()
    if "claim" in blob:
        return "Claim payload"
    if "payment" in blob or "settlement" in blob:
        return "Payment payload"
    if "order" in blob:
        return "Order payload"
    if "event" in blob and "stream" in blob:
        return "Domain event"
    if sensitive:
        return "Sensitive domain payload"
    return "Domain payload"
