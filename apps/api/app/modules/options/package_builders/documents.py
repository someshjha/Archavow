"""MVP architecture document builders (overview, requirements, plans, etc.)."""

from __future__ import annotations

from typing import Any

from app.modules.options.generator import OptionTemplate, ProjectContext

# Artifact codes — keep in sync with docs/ARTIFACT_CATALOG.md
MVP_MANDATORY = (
    "overview",
    "requirements",
    "options_comparison",
    "hld",
    "roadmap",
    "migration_plan",
    "operational_readiness",
    "review_record",
)
MVP_CONDITIONAL = (
    "standards_mapping",
    "cost_model",
    "traceability",
)


def _bullets(items: list[str], empty: str = "- _(none captured yet)_") -> str:
    cleaned = [str(x).strip() for x in items if str(x).strip()]
    if not cleaned:
        return empty
    return "\n".join(f"- {x}" for x in cleaned)


def _section(title: str, body: str) -> str:
    return f"## {title}\n\n{body.strip()}\n"


def build_overview_markdown(
    ctx: ProjectContext,
    option: OptionTemplate,
    *,
    executive_summary: str | None = None,
) -> str:
    parts = [
        f"# {ctx.name} — Architecture overview",
        "",
        _section("Business objective", ctx.business_objective or "_(not stated)_"),
        _section("Problem statement", ctx.problem_statement or "_(not stated)_"),
        _section(
            "Scope and system boundaries",
            (
                f"Working option: **{option.title}**.\n\n"
                f"{(option.approach or option.summary).strip() or '_(approach not recorded)_'}\n\n"
                f"In scope: the system described by intake and interview answers.\n"
                "Out of scope until named: unrelated enterprise platforms, org-wide "
                "identity redesign, and vendor evaluations not evidenced in constraints."
            ),
        ),
        _section(
            "Stakeholders and users",
            (
                "Primary stakeholders: solution architect (author), platform/ops, "
                "security review, and delivery leads.\n"
                "Users / callers: inferred from interview and domain language — "
                "confirm in the requirements document if still fuzzy."
            ),
        ),
        _section(
            "Current-state summary",
            (
                f"Cloud / landing zone: **{ctx.preferred_cloud or 'not picked yet'}**.\n"
                f"Scale / availability notes: {ctx.scale_availability or '—'}.\n"
                f"Tech constraints: {ctx.tech_constraints or '—'}.\n"
                "Treat this as the as-is constraint set until a formal current-state "
                "assessment is attached."
            ),
        ),
    ]
    if executive_summary and executive_summary.strip():
        parts.insert(2, _section("In short", executive_summary.strip()))
    return "\n".join(parts).rstrip() + "\n"


def build_requirements_markdown(
    ctx: ProjectContext,
    option: OptionTemplate,
    *,
    open_questions: list[str] | None = None,
    completeness: dict[str, Any] | None = None,
) -> str:
    reqs = [r for r in ctx.requirements if str(r).strip()]
    frs = [r for r in reqs if not _looks_nfr(r)]
    nfrs = [r for r in reqs if _looks_nfr(r)]
    if not nfrs and ctx.scale_availability:
        nfrs.append(ctx.scale_availability)
    open_q = list(open_questions or [])
    comp = completeness or {}
    gaps = [str(g) for g in (comp.get("gaps") or []) if str(g).strip()]
    for g in gaps:
        if g not in open_q:
            open_q.append(f"Structural gap still open: `{g}`")

    return "\n".join(
        [
            f"# {ctx.name} — Requirements",
            "",
            _section("Functional requirements", _bullets(frs)),
            _section("Non-functional requirements", _bullets(nfrs)),
            _section(
                "Constraints and assumptions",
                (
                    f"**Intake constraints:** {ctx.tech_constraints or '—'}\n\n"
                    f"**Option constraints:**\n{_bullets(list(option.constraints or []))}\n\n"
                    f"**Assumptions:**\n{_bullets(list(option.assumptions or []))}"
                ),
            ),
            _section(
                "Dependencies",
                _bullets(
                    [
                        *(f"Stack dependency: {s}" for s in option.stack),
                        *(
                            ["Cloud / landing zone decision still open"]
                            if not (ctx.preferred_cloud or "").strip()
                            else [f"Landing zone: {ctx.preferred_cloud}"]
                        ),
                    ]
                ),
            ),
            _section(
                "Acceptance criteria",
                _bullets(
                    [
                        "Selected option fits stated objective and problem statement",
                        "Open P0 interview gaps closed or explicitly deferred with owner",
                        "ADRs for contested decisions reviewed by stakeholders",
                        *(
                            [f"Quality score evidence gaps addressed: {m}"]
                            for m in (comp.get("missing_evidence") or [])[:3]
                        ),
                    ]
                ),
            ),
            _section("Open questions", _bullets(open_q, "- _(none flagged)_")),
        ]
    ).rstrip() + "\n"


def _looks_nfr(text: str) -> bool:
    t = text.lower()
    markers = (
        "rto",
        "rpo",
        "latency",
        "throughput",
        "sla",
        "slo",
        "availability",
        "99.",
        "security",
        "compliance",
        "encryption",
        "pii",
        "gdpr",
        "cost",
        "scale",
        "peak",
        "events/sec",
        "ops",
    )
    return any(m in t for m in markers)


def build_options_comparison_markdown(
    ctx: ProjectContext,
    options: list[dict[str, Any]],
    selected: OptionTemplate,
) -> str:
    lines = [
        f"# {ctx.name} — Architecture options",
        "",
        "At least two viable alternatives were considered. Fit scores are relative "
        "to captured requirements — not a certification.",
        "",
    ]
    if len(options) < 2:
        lines.append("_Fewer than two options were available when this package was built._\n")
    for opt in options:
        design = opt.get("design") if isinstance(opt.get("design"), dict) else {}
        marker = " **(selected)**" if opt.get("selected") else ""
        if opt.get("recommended") and not opt.get("selected"):
            marker += " _(recommended at generate time)_"
        lines.extend(
            [
                f"## {opt.get('title', 'Option')}{marker}",
                "",
                str(opt.get("summary") or ""),
                "",
                f"- Fit: {opt.get('fit_score', '—')} · Cost band: {opt.get('cost_band', '—')} · "
                f"Ops band: {opt.get('ops_band', '—')}",
                f"- Stack: {', '.join(opt.get('stack') or []) or '—'}",
                "",
                "### Benefits",
                _bullets(list(opt.get("pros") or [])),
                "",
                "### Drawbacks",
                _bullets(list(opt.get("cons") or [])),
                "",
                "### Security and reliability implications",
                (
                    f"Ops load **{opt.get('ops_band', '—')}** implies on-call and failure-mode "
                    "work proportional to that band. Security controls still need explicit "
                    "auth, least privilege, and (where messaging exists) ACL/retention review."
                ),
                "",
                "### Fit against requirements",
                str(design.get("approach") or opt.get("summary") or "_(no approach recorded)_"),
                "",
            ]
        )
    lines.extend(
        [
            "## Recommended option with rationale",
            "",
            f"**{selected.title}** is the packaged choice.",
            "",
            (selected.approach or selected.summary).strip() or "_(rationale thin — expand via interview)_",
            "",
            "Key decisions to lock:",
            _bullets(list(selected.key_decisions or []), "- _(none recorded)_"),
            "",
        ]
    )
    return "\n".join(lines)


def build_roadmap_markdown(ctx: ProjectContext, option: OptionTemplate, backlog: list[dict]) -> str:
    p0 = [b for b in backlog if str(b.get("priority") or "").upper() == "P0"]
    p1 = [b for b in backlog if str(b.get("priority") or "").upper() == "P1"]
    return "\n".join(
        [
            f"# {ctx.name} — Implementation roadmap",
            "",
            _section(
                "Major workstreams",
                _bullets(
                    [
                        "Foundation: auth, observability, landing-zone wiring",
                        f"Core delivery for **{option.title}**",
                        "Reliability drills (failover / restore) before production claims",
                        "Governance: ADR walkthrough and package export for review",
                    ]
                ),
            ),
            _section(
                "Dependencies and sequencing",
                (
                    "1. Close P0 interview / security gaps\n"
                    "2. Land foundation (auth + golden signals)\n"
                    "3. Deliver core path for the selected option\n"
                    "4. Run reliability game day\n"
                    "5. Architecture review and handoff export"
                ),
            ),
            _section(
                "Milestones",
                _bullets(
                    [
                        "M1 — Foundation ready (auth + signals)",
                        "M2 — Core path demoable against acceptance criteria",
                        "M3 — DR drill evidence attached",
                        "M4 — Review approved / accepted risks recorded",
                    ]
                ),
            ),
            _section(
                "Migration phases",
                (
                    "Phase 0: no production cutover — build beside current state.\n"
                    "Phase 1: shadow or limited cohort if replacing an existing system.\n"
                    "Phase 2: cutover per migration plan; keep rollback criteria green.\n"
                    "Phase 3: decommission legacy only after soak criteria met."
                ),
            ),
            _section(
                "Ownership",
                (
                    f"- Architecture: solution architect for {ctx.name}\n"
                    f"- Delivery: feature team owning **{option.title}**\n"
                    "- Platform / ops: on-call for runtime and brokers\n"
                    "- Security: threat model and write-path auth review"
                ),
            ),
            _section(
                "Near-term backlog anchors",
                _bullets(
                    [f"{b.get('id')}: {b.get('title')}" for b in (p0 + p1)[:8]],
                    "- _(backlog empty)_",
                ),
            ),
        ]
    ).rstrip() + "\n"


def build_migration_plan_markdown(ctx: ProjectContext, option: OptionTemplate) -> str:
    return "\n".join(
        [
            f"# {ctx.name} — Migration and deployment plan",
            "",
            _section(
                "Current-to-target transition",
                (
                    f"Target shape: **{option.title}** ({', '.join(option.stack) or 'stack TBD'}).\n"
                    "Run the new path beside current-state until acceptance criteria pass, "
                    "then cut traffic deliberately — not as a big-bang surprise."
                ),
            ),
            _section(
                "Data migration",
                (
                    "Identify system-of-record tables/topics that must move or dual-write.\n"
                    "Prefer expand/contract: add new writers, backfill, switch readers, "
                    "then remove legacy writers. Capture RPO implications in the interview."
                ),
            ),
            _section(
                "Blue-green / canary strategy",
                (
                    "Default: canary a small % of traffic (or a cohort) to the new path, "
                    "watch golden signals and error budgets, then ramp.\n"
                    "Blue-green is preferred when stateful dual-write is too risky."
                ),
            ),
            _section(
                "Cutover steps",
                (
                    "1. Freeze or dampen non-critical writes if required\n"
                    "2. Verify backups / snapshots and migration job completion\n"
                    "3. Flip traffic (canary → full) with feature flag or DNS/gateway weight\n"
                    "4. Validate SLO burn and key business transactions\n"
                    "5. Keep legacy warm until soak window ends"
                ),
            ),
            _section(
                "Rollback criteria",
                _bullets(
                    [
                        "Error rate or latency exceeds error budget for N minutes",
                        "Data divergence / RPO breach detected",
                        "Critical auth or write-path failure",
                        "On-call declares rollback — no heroics",
                    ]
                ),
            ),
            _section(
                "Decommissioning plan",
                (
                    "After soak: disable legacy writers, archive data per retention policy, "
                    "remove unused infra, and update runbooks/ADRs to match reality."
                ),
            ),
        ]
    ).rstrip() + "\n"


def build_operational_readiness_markdown(ctx: ProjectContext, option: OptionTemplate) -> str:
    scale = ctx.scale_availability or "_(scale / SLO still open — close in interview)_"
    return "\n".join(
        [
            f"# {ctx.name} — Operational readiness plan",
            "",
            _section("Service-level objectives", scale),
            _section(
                "Monitoring and alerting",
                (
                    "Golden signals (latency, traffic, errors, saturation) on edge, app, "
                    "datastore, and messaging if present.\n"
                    f"Ops band **{option.ops_band}** — page only on user-visible burn."
                ),
            ),
            _section(
                "Logging and tracing",
                (
                    "Structured logs with correlation IDs across API → services → bus → SoR.\n"
                    "Distributed traces for the critical write path before go-live."
                ),
            ),
            _section(
                "Capacity assumptions",
                (
                    f"Scale note: {scale}\n"
                    "Size for stated peak + headroom; document autoscaling limits and "
                    "broker/partition ceilings."
                ),
            ),
            _section(
                "Backup and recovery",
                (
                    "Automated backups for the system of record; tested restore path.\n"
                    "Align restore drills with stated RTO/RPO (see risk register)."
                ),
            ),
            _section(
                "Incident response",
                (
                    "Named on-call, severity definitions, and escalation to platform/security.\n"
                    "Post-incident review within 5 business days for Sev-1/2."
                ),
            ),
            _section(
                "Runbook requirements",
                _bullets(
                    [
                        "Deploy / rollback",
                        "Failover / restore",
                        "Poison message / DLQ handling (if messaging)",
                        "Certificate and secret rotation",
                        "Capacity ramp for known peaks",
                    ]
                ),
            ),
        ]
    ).rstrip() + "\n"


def build_review_record_markdown(
    ctx: ProjectContext,
    option: OptionTemplate,
    *,
    quality_score: dict[str, Any] | None = None,
) -> str:
    """Human architecture sign-off stub — not an implementation-code lint report."""
    score = quality_score or {}
    required: list[str] = []
    for m in score.get("missing_evidence") or []:
        required.append(f"Evidence gap: {m}")
    for b in score.get("blockers") or []:
        required.append(f"Blocker: {b}")

    return "\n".join(
        [
            f"# {ctx.name} — Architecture review record",
            "",
            _section(
                "Reviewers",
                (
                    "- Solution architect (author)\n"
                    "- Platform / ops representative\n"
                    "- Security reviewer\n"
                    "- Delivery lead\n"
                    "_(Names TBD — fill before approval)_"
                ),
            ),
            _section(
                "Discussion notes",
                "- _(Capture design concerns from the package walkthrough)_",
            ),
            _section(
                "Required changes",
                _bullets(required, "- _(none flagged from quality checklist)_"),
            ),
            _section(
                "Accepted risks",
                "- _(none recorded — see risk register)_",
            ),
            _section(
                "Approval status",
                (
                    "**Status:** draft — pending human architecture sign-off\n\n"
                    f"Selected option: **{option.title}**.\n"
                    f"Evidence checklist coverage: {score.get('overall', '—')}."
                ),
            ),
        ]
    ).rstrip() + "\n"


def build_standards_mapping_markdown(
    ctx: ProjectContext,
    citations: list[dict[str, Any]],
) -> str:
    """Conditional artifact — light mapping from retrieved citations."""
    lines = [
        f"# {ctx.name} — Standards and compliance mapping",
        "",
        "_Conditional artifact. Expand when org standards or regulations apply._",
        "",
        _section(
            "Applicable organizational standards",
            _bullets(
                [
                    f"[{c.get('source_class')}] {c.get('citation') or c.get('title')}"
                    for c in citations
                    if str(c.get("source_class") or "") in {"org", "seed"}
                ],
                "- _(none retrieved — add org standards to Knowledge)_",
            ),
        ),
        _section(
            "Regulatory obligations",
            "- _(not assessed in MVP — mark explicitly if GDPR/PCI/HIPAA/etc. apply)_",
        ),
        _section(
            "Exceptions and waivers",
            "- _(none recorded)_",
        ),
        _section(
            "Supporting evidence",
            _bullets(
                [
                    (c.get("excerpt") or c.get("text") or "")[:200]
                    for c in citations[:8]
                    if (c.get("excerpt") or c.get("text"))
                ],
                "- _(no citation excerpts)_",
            ),
        ),
    ]
    return "\n".join(lines).rstrip() + "\n"


def build_cost_model_markdown(ctx: ProjectContext, option: OptionTemplate) -> str:
    """Conditional artifact — bands only until a real cost model exists."""
    return "\n".join(
        [
            f"# {ctx.name} — Cost model (draft)",
            "",
            "_Conditional artifact. Bands are relative, not a quote._",
            "",
            _section(
                "Expected infrastructure cost",
                f"Relative band for **{option.title}**: **{option.cost_band}**.",
            ),
            _section(
                "Major cost drivers",
                _bullets(
                    [
                        f"Runtime / platform implied by stack: {', '.join(option.stack) or 'TBD'}",
                        f"Ops load band: {option.ops_band}",
                        "Data transfer, retention, and multi-region if chosen",
                    ]
                ),
            ),
            _section(
                "Growth assumptions",
                ctx.scale_availability or "_(peak / growth not stated)_",
            ),
            _section(
                "Cost controls and budgets",
                (
                    "Set a monthly budget alert on the landing zone; review retention and "
                    "idle environments quarterly. Revisit band if multi-region or always-on "
                    "DR is accepted."
                ),
            ),
        ]
    ).rstrip() + "\n"


def build_traceability_markdown(
    ctx: ProjectContext,
    option: OptionTemplate,
    *,
    adrs: list[dict],
    risks: list[dict],
    backlog: list[dict],
) -> str:
    """Conditional artifact — lightweight requirement → decision → work links."""
    req_lines = []
    for i, r in enumerate(ctx.requirements[:12], start=1):
        req_lines.append(f"| FR/NFR-{i:02d} | {r[:80]} | {option.title} | ADR-001 |")
    if not req_lines:
        req_lines.append("| — | _(no requirements captured)_ | — | — |")

    risk_lines = [
        f"| {r.get('id')} | {r.get('mitigation', '')[:80]} |" for r in risks[:8]
    ] or ["| — | _(no risks)_ |"]

    decision_lines = [
        f"| {a.get('id')} | next backlog item covering “{a.get('title', '')[:60]}” |"
        for a in adrs[:8]
    ] or ["| — | — |"]

    return "\n".join(
        [
            f"# {ctx.name} — Traceability matrix (draft)",
            "",
            "_Conditional artifact. Full req→control→impl chain is post-MVP._",
            "",
            "## Requirement → decision / component",
            "",
            "| ID | Requirement (excerpt) | Component / option | Decision |",
            "|----|----------------------|--------------------|----------|",
            *req_lines,
            "",
            "## Risk → mitigation",
            "",
            "| Risk | Mitigation |",
            "|------|------------|",
            *risk_lines,
            "",
            "## Decision → implementation item",
            "",
            "| Decision | Implementation cue |",
            "|----------|--------------------|",
            *decision_lines,
            "",
            "## Evidence → architecture claim",
            "",
            "| Claim | Evidence |",
            "|-------|----------|",
            f"| Selected option fit | Package quality score + interview answers |",
            f"| Stack choice | Constraints: {ctx.tech_constraints or '—'} |",
            f"| Near-term work | Backlog items: {', '.join(b.get('id','') for b in backlog[:6]) or '—'} |",
            "",
        ]
    )


def build_package_documents(
    ctx: ProjectContext,
    option: OptionTemplate,
    *,
    options: list[dict[str, Any]],
    backlog: list[dict],
    adrs: list[dict],
    risks: list[dict],
    citations: list[dict[str, Any]],
    quality_score: dict[str, Any],
    hld_markdown: str,
    executive_summary: str | None = None,
    open_questions: list[str] | None = None,
    completeness: dict[str, Any] | None = None,
    include_conditional: bool = True,
) -> dict[str, str]:
    """Return markdown documents keyed by artifact code."""
    docs: dict[str, str] = {
        "overview": build_overview_markdown(
            ctx, option, executive_summary=executive_summary
        ),
        "requirements": build_requirements_markdown(
            ctx,
            option,
            open_questions=open_questions,
            completeness=completeness,
        ),
        "options_comparison": build_options_comparison_markdown(ctx, options, option),
        "hld": hld_markdown,
        "roadmap": build_roadmap_markdown(ctx, option, backlog),
        "migration_plan": build_migration_plan_markdown(ctx, option),
        "operational_readiness": build_operational_readiness_markdown(ctx, option),
        "review_record": build_review_record_markdown(
            ctx, option, quality_score=quality_score
        ),
    }
    if include_conditional:
        docs["standards_mapping"] = build_standards_mapping_markdown(ctx, citations)
        docs["cost_model"] = build_cost_model_markdown(ctx, option)
        docs["traceability"] = build_traceability_markdown(
            ctx, option, adrs=adrs, risks=risks, backlog=backlog
        )
    return docs
