"""High-level design markdown."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from app.ai.hld_assist import generate_hld_content
from app.ai.schemas import ChatModelRef, EffectiveAIConfig
from app.modules.options.generator import OptionTemplate, ProjectContext
from app.modules.options.package_builders._shared import _context_blob

if TYPE_CHECKING:
    from app.ai.gateway import AIGateway


def _bullets(items: list[str], empty: str) -> str:
    cleaned = [str(x).strip() for x in items if str(x).strip()]
    if not cleaned:
        return empty
    return "\n".join(f"- {x}" for x in cleaned)


def _template_sections(ctx: ProjectContext, option: OptionTemplate) -> dict[str, str]:
    """Deterministic, keyword-evidenced content for the 7 structured HLD
    sections — the guaranteed fallback when AI is unavailable."""
    stack_l = {s.lower() for s in option.stack}
    blob = _context_blob(ctx)
    components: list[str] = [f"- Stack on the table: {', '.join(option.stack) or 'still open'}"]
    if any(k in stack_l or k in blob for k in ("gateway", "ingress", "api", "rest", "http")):
        components.append("- Edge / API ingress (called out in constraints or stack)")
    if any(
        k in stack_l or k in blob for k in ("postgres", "sql", "cosmos", "database", "store")
    ):
        components.append("- System of record (a data store showed up in intake/stack)")
    if any(
        k in stack_l or k in blob
        for k in ("kafka", "service-bus", "queue", "messaging", "event", "pubsub")
    ):
        components.append("- Messaging / events (from stack or constraints)")
    if any(
        k in stack_l or k in blob
        for k in (
            "aks",
            "eks",
            "gke",
            "kubernetes",
            "k8s",
            "container-apps",
            "serverless",
            "containers",
        )
    ):
        components.append("- App runtime (containers or serverless as selected)")
    if len(components) == 1:
        components.append("- _(thin so far — interview should fill this in)_")

    return {
        "component_responsibilities": chr(10).join(components),
        "technology_choices": (
            f"- Selected stack tags: {', '.join(option.stack) or 'still open'}\n"
            f"- Landing zone: {ctx.preferred_cloud or 'not picked yet'}\n"
            f"- Cost / ops bands: {option.cost_band} / {option.ops_band}"
        ),
        "integration_patterns": (
            "- Prefer sync APIs for request/response user paths; async messaging where "
            "fan-out, buffering, or decoupling is evidenced.\n"
            "- Keep correlation IDs across edge → services → bus → SoR."
        ),
        "data_ownership": (
            "- System of record: Postgres (or the store named in constraints/stack) "
            "owns authoritative writes.\n"
            "- Derived views / consumers must not silently become a second SoR."
        ),
        "api_event_boundaries": (
            "- External clients enter via the edge/API only.\n"
            "- Domain events (if any) are contracts — version payloads; don't leak "
            "internal tables."
        ),
        "scaling_availability": (
            f"- Scale note: {ctx.scale_availability or '_(still open — close in interview)_'}\n"
            f"- Ops band **{option.ops_band}** drives on-call and capacity discipline."
        ),
        "failure_handling": (
            "- Timeouts and retries with backoff on outbound calls; idempotent writes "
            "where at-least-once delivery applies.\n"
            "- DLQ / poison handling for messaging; documented rollback on cutover "
            "(see migration plan)."
        ),
    }


def _ai_sections(content: dict[str, Any]) -> dict[str, str]:
    """Render generate_hld_content()'s structured result into the same 7
    section keys _template_sections() produces."""
    tech_lines = [
        f"- **{t.get('area', '?')}**: {t.get('technology', '?')} — {t.get('why', '')}"
        for t in content.get("technology_choices") or []
        if isinstance(t, dict)
    ]
    return {
        "component_responsibilities": _bullets(
            [str(x) for x in content.get("component_responsibilities") or []],
            "- _(thin so far — interview should fill this in)_",
        ),
        "technology_choices": _bullets(tech_lines, "- _(still open)_"),
        "integration_patterns": _bullets(
            [str(x) for x in content.get("integration_patterns") or []], "- _(still open)_"
        ),
        "data_ownership": _bullets(
            [str(x) for x in content.get("data_ownership") or []], "- _(still open)_"
        ),
        "api_event_boundaries": _bullets(
            [str(x) for x in content.get("api_event_boundaries") or []], "- _(still open)_"
        ),
        "scaling_availability": _bullets(
            [str(x) for x in content.get("scaling_availability") or []], "- _(still open)_"
        ),
        "failure_handling": _bullets(
            [str(x) for x in content.get("failure_handling") or []], "- _(still open)_"
        ),
    }


def _render(
    ctx: ProjectContext,
    option: OptionTemplate,
    sections: dict[str, str],
    *,
    citations: list[dict] | None,
    executive_summary: str | None,
    extra_assumptions: list[str] | None = None,
) -> str:
    reqs = "\n".join(f"- {r}" for r in ctx.requirements) or "- _(nothing captured yet)_"
    pros = "\n".join(f"- {p}" for p in option.pros)
    cons = "\n".join(f"- {c}" for c in option.cons)
    cites = citations or []
    if cites:
        std_lines = "\n".join(
            f"- [{c.get('source_class', 'org')}] {c.get('citation', c.get('title', 'standard'))}"
            f" — {(c.get('excerpt') or c.get('text') or '')[:160]}"
            for c in cites
        )
        standards_section = f"""## Standards we pulled in
{std_lines}
"""
    else:
        standards_section = """## Standards we pulled in
- _(none yet — drop org standards into Knowledge if you want citations here)_
"""
    exec_section = ""
    if executive_summary and executive_summary.strip():
        exec_section = f"""## In short
{executive_summary.strip()}

"""
    blob = _context_blob(ctx)
    assumptions = [a for a in (option.assumptions or []) if str(a).strip()]
    seen_assumptions = {a.strip() for a in assumptions}
    for a in extra_assumptions or []:
        cleaned = str(a).strip()
        if cleaned and cleaned not in seen_assumptions:
            assumptions.append(cleaned)
            seen_assumptions.add(cleaned)
    if not assumptions:
        if not any(
            k in blob for k in ("oidc", "oauth", "authn", "authz", "mtls", "rbac", "jwt", "sso")
        ):
            assumptions.append("How callers authenticate is still fuzzy")
        if not any(k in blob for k in ("rto", "rpo", "backup", "dr", "failover")):
            assumptions.append("No hard RTO/RPO or backup story yet")
        if not any(
            k in blob for k in ("observability", "metrics", "tracing", "on-call", "slo")
        ):
            assumptions.append("Observability / on-call still blank")
        if "network" not in blob and "private" not in blob and "vnet" not in blob:
            assumptions.append("Private networking / segmentation not spelled out")
    assumptions_block = _bullets(
        assumptions,
        "- _(main control gaps look covered in intake/interview)_",
    )
    constraints_block = _bullets(
        list(option.constraints or []),
        "- _(none recorded on this option — see intake constraints above)_",
    )
    decisions_block = _bullets(
        list(option.key_decisions or []),
        "- _(none recorded — ADRs below capture contested choices)_",
    )
    approach_section = ""
    if (option.approach or "").strip():
        approach_section = f"""## How this approach works
{option.approach.strip()}

"""
    origin_note = ""
    if getattr(option, "origin", "template") == "template":
        origin_note = (
            "\n> **Working draft.** This came from a starter template, not a ranked bake-off. "
            "Treat the pieces below as a sketch until the interview fills the gaps.\n"
        )
    rank_note = (
        f"draft rank {option.fit_score}/3"
        if getattr(option, "origin", "template") == "template"
        else f"fit {option.fit_score}"
    )
    return f"""# {ctx.name} — High-level design
{origin_note}
{exec_section}## Option we're packing
**{option.title}** ({rank_note}; cost {option.cost_band}; ops {option.ops_band})

{option.summary}

{approach_section}### Why it might work
{pros}

### What you'll pay for it
{cons}

## Design constraints
{constraints_block}

## Assumptions
{assumptions_block}

## Key decisions to lock
{decisions_block}

## Where this sits
- Objective: {ctx.business_objective or "—"}
- Problem: {ctx.problem_statement or "—"}
- Cloud: **{ctx.preferred_cloud or "not picked yet"}**
- Constraints: {ctx.tech_constraints or "—"}
- Scale: {ctx.scale_availability or "—"}

## Requirements on the board
{reqs}

{standards_section}
## Component responsibilities
{sections["component_responsibilities"]}

## Technology choices
{sections["technology_choices"]}

## Integration patterns
{sections["integration_patterns"]}

## Data ownership and storage
{sections["data_ownership"]}

## API and event boundaries
{sections["api_event_boundaries"]}

## Scaling and availability strategy
{sections["scaling_availability"]}

## Failure-handling approach
{sections["failure_handling"]}

## Suggested next step
Finish open interview questions, walk ADRs and risks, then export the handoff package for review.
"""


def build_hld_markdown(
    ctx: ProjectContext,
    option: OptionTemplate,
    citations: list[dict] | None = None,
    executive_summary: str | None = None,
) -> str:
    """Deterministic HLD markdown — unchanged signature/behavior. Used
    directly by callers that don't need AI, and as the guaranteed fallback
    inside build_hld_markdown_ai when every model fails."""
    return _render(
        ctx,
        option,
        _template_sections(ctx, option),
        citations=citations,
        executive_summary=executive_summary,
    )


def build_hld_markdown_ai(
    ctx: ProjectContext,
    option: OptionTemplate,
    *,
    citations: list[dict] | None,
    executive_summary: str | None,
    fallback_chain: list[ChatModelRef],
    base_config: EffectiveAIConfig,
    gateway_factory: Callable[[EffectiveAIConfig], AIGateway],
) -> tuple[str, str, str | None]:
    """AI-grounded HLD when possible; falls back to build_hld_markdown()
    (byte-identical to the deterministic path) when every model fails.
    Returns (markdown, hld_source, hld_model) where hld_source is
    'ai' or 'template'."""
    content, entry, _status = generate_hld_content(
        ctx,
        option,
        citations=citations,
        fallback_chain=fallback_chain,
        base_config=base_config,
        gateway_factory=gateway_factory,
    )
    if content is None:
        return (
            build_hld_markdown(
                ctx, option, citations=citations, executive_summary=executive_summary
            ),
            "template",
            None,
        )
    extra_assumptions = [str(a) for a in content.get("assumptions") or [] if str(a).strip()]
    markdown = _render(
        ctx,
        option,
        _ai_sections(content),
        citations=citations,
        executive_summary=executive_summary,
        extra_assumptions=extra_assumptions,
    )
    model = f"{entry.provider}/{entry.model}" if entry else None
    return markdown, "ai", model
