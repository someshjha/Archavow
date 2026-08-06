"""Markdown renderers for exported package artifacts."""

from __future__ import annotations


def render_adr_markdown(adr: dict) -> str:
    cons = "\n".join(f"- {c}" for c in adr.get("consequences") or [])
    alts = "\n".join(f"- {a}" for a in adr.get("alternatives") or []) or "- _(none recorded)_"
    rationale = str(adr.get("rationale") or "").strip() or "_(none recorded)_"
    owner = adr.get("owner") or "unassigned"
    return (
        f"# {adr['id']}: {adr['title']}\n\n"
        f"**Status:** {adr.get('status', 'proposed')}  \n"
        f"**Owner:** {owner}\n\n"
        f"## Context\n\n{adr.get('context', '')}\n\n"
        f"## Decision\n\n{adr.get('decision', '')}\n\n"
        f"## Alternatives considered\n\n{alts}\n\n"
        f"## Rationale\n\n{rationale}\n\n"
        f"## Consequences\n\n{cons}\n"
    )


def render_risk_register_markdown(risks: list[dict]) -> str:
    lines = ["# Risk register", ""]
    for r in risks:
        lines.extend(
            [
                f"## {r['id']} — {r['title']}",
                "",
                f"- Category: {r.get('category', '')}",
                f"- Severity: {r.get('severity', '')}",
                f"- Likelihood: {r.get('likelihood', '')}",
                f"- Owner: {r.get('owner') or 'unassigned'}",
                f"- Target date: {r.get('target_date') or 'TBD'}",
                "",
                "### Impact",
                r.get("impact") or "",
                "",
                "### Mitigation",
                r.get("mitigation") or "",
                "",
                "### Residual risk",
                r.get("residual_risk") or "_(not assessed)_",
                "",
            ]
        )
    return "\n".join(lines)


def render_backlog_markdown(items: list[dict]) -> str:
    lines = ["# Architecture backlog", ""]
    for b in items:
        ac = b.get("acceptance_criteria") or []
        deps = b.get("dependencies") or []
        lines.extend(
            [
                f"## {b['id']} — {b['title']}",
                "",
                f"- Priority: {b.get('priority', '')}",
                f"- Area: {b.get('area', '')}",
                f"- Type: {b.get('item_type') or 'enabler'}",
                f"- Dependencies: {', '.join(str(d) for d in deps) or 'none'}",
                "",
                b.get("notes") or "",
                "",
                "### Acceptance criteria",
            ]
        )
        if ac:
            lines.extend(f"- {x}" for x in ac)
        else:
            lines.append("- _(none recorded)_")
        lines.append("")
    return "\n".join(lines)


def render_epics_markdown(epics: list[dict], *, requirements: list[str] | None = None) -> str:
    lines = [
        "# Delivery backlog — epics and user stories",
        "",
        "Business epics with user stories, plus technical enabler stories. Each story "
        "traces to the requirement that justified it (see the requirement index below).",
        "",
    ]
    reqs = [r for r in (requirements or []) if str(r).strip()]
    if reqs:
        lines.extend(["## Requirement index", ""])
        lines.extend(
            f"- **R-{i + 1:03d}** — {' '.join(str(r).split())}" for i, r in enumerate(reqs)
        )
        lines.append("")

    for epic in epics:
        stories = list(epic.get("stories") or [])
        refs = ", ".join(str(r) for r in (epic.get("requirement_refs") or [])) or "—"
        lines.extend(
            [
                f"## {epic.get('id', '')} — {epic.get('title', '')}",
                "",
                f"- Priority: {epic.get('priority', '')}",
                f"- Requirements: {refs}",
                f"- Stories: {len(stories)}",
                "",
                f"**Why this is needed.** {epic.get('need', '')}",
                "",
                f"**Outcome.** {epic.get('business_outcome', '')}",
                "",
            ]
        )
        for story in stories:
            story_refs = ", ".join(str(r) for r in (story.get("requirement_refs") or [])) or "—"
            deps = ", ".join(str(d) for d in (story.get("dependencies") or [])) or "none"
            lines.extend(
                [
                    f"### {story.get('id', '')} — {story.get('title', '')}",
                    "",
                    f"- Type: {story.get('type') or 'business'}",
                    f"- Priority: {story.get('priority', '')}",
                    f"- Traces to: {story_refs}",
                    f"- Depends on: {deps}",
                    "",
                ]
            )
            if story.get("need"):
                lines.extend([f"_{story['need']}_", ""])
            lines.extend(["**Acceptance criteria**", ""])
            criteria = list(story.get("acceptance_criteria") or [])
            if criteria:
                for ac in criteria:
                    lines.extend(
                        [
                            f"- **{ac.get('id', 'AC')}**",
                            f"  - Given {ac.get('given', '')}",
                            f"  - When {ac.get('when', '')}",
                            f"  - Then {ac.get('then', '')}",
                        ]
                    )
            else:
                lines.append("- _(none recorded)_")
            lines.append("")
            checks = list(story.get("nfr_checks") or [])
            if checks:
                lines.extend(["**Non-functional checks**", ""])
                lines.extend(f"- {c}" for c in checks)
                lines.append("")
    return "\n".join(lines)


def render_threats_markdown(threats: list[dict]) -> str:
    lines = [
        "# Threat model (STRIDE-lite)",
        "",
        "Assets, trust boundaries, scenarios, and controls for decision support. "
        "Expand to a full threat model when risk warrants it.",
        "",
    ]
    for t in threats:
        lines.extend(
            [
                f"## {t['id']} — {t.get('stride', '')}",
                "",
                f"- Asset: {t.get('asset', '')}",
                f"- Trust boundary: {t.get('boundary', '')}",
                "",
                "### Threat scenario",
                t.get("threat") or "",
                "",
                "### Security controls",
                t.get("controls") or t.get("mitigation") or "",
                "",
                "### Unresolved security risks",
                t.get("unresolved") or "_(none flagged)_",
                "",
                "### Privacy and compliance",
                t.get("privacy") or "_(not assessed for this asset)_",
                "",
            ]
        )
    return "\n".join(lines)


def render_score_markdown(score: dict) -> str:
    lines = [
        "# Architecture evidence checklist",
        "",
        f"**Overall coverage:** {score.get('overall', 'missing')}",
        "",
        "_Coverage states from intake/interview — not a certification score._",
        "",
        "## Categories",
        "",
    ]
    for c in score.get("categories") or []:
        coverage = c.get("coverage") or c.get("score", "—")
        lines.append(
            f"- **{c.get('label')}** (weight {c.get('weight')}%): {coverage}"
        )
    missing = score.get("missing_evidence") or []
    blockers = score.get("blockers") or []
    lines.extend(["", "## Identified evidence gaps", ""])
    if missing:
        lines.extend(f"- {m}" for m in missing)
    else:
        lines.append("- None flagged")
    lines.extend(["", "## Blockers", ""])
    if blockers:
        lines.extend(f"- {b}" for b in blockers)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)
