"""Build git-friendly export file trees from the architecture package."""

from __future__ import annotations

import json
import re
from typing import Any

# path → documents key, in MVP catalog order (docs/ARTIFACT_CATALOG.md) so the
# README contents list reads 1 → 18 instead of jumping between artifact numbers.
_DOCUMENT_EXPORT_PATHS: dict[str, str] = {
    "overview/architecture-overview.md": "overview",
    "requirements/requirements.md": "requirements",
    "options/comparison.md": "options_comparison",
    "governance/standards-mapping.md": "standards_mapping",
    "delivery/roadmap.md": "roadmap",
    "delivery/migration-plan.md": "migration_plan",
    "ops/operational-readiness.md": "operational_readiness",
    "cost/cost-model.md": "cost_model",
    "review/architecture-review.md": "review_record",
    "traceability/matrix.md": "traceability",
}

# documents key → catalog number, for the README contents list.
_DOCUMENT_CATALOG_NUMBERS: dict[str, int] = {
    "overview": 1,
    "requirements": 2,
    "options_comparison": 3,
    "hld": 5,
    "standards_mapping": 10,
    "roadmap": 11,
    "migration_plan": 14,
    "operational_readiness": 15,
    "cost_model": 16,
    "review_record": 17,
    "traceability": 18,
}


def _contents_line(number: int | None, path: str) -> str:
    return f"- `{number}` · `{path}`" if number else f"- `{path}`"


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return (s[:48] or "item")


def build_export_files(
    *,
    project: dict[str, Any],
    package: dict[str, Any] | None,
    selected_option: dict[str, Any] | None,
    include_hld: bool,
    include_mermaid: bool,
    include_adrs: bool,
    include_risks: bool,
    include_project_json: bool,
) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    name = project.get("name") or "project"
    docs = dict((package or {}).get("documents") or {})
    parts = [
        f"# {name} — Archavow export",
        "",
        "Git-friendly handoff package. Leading numbers are MVP artifact catalog "
        "numbers, listed in catalog order.",
        "",
        "## Contents",
    ]

    def doc_lines(key: str) -> list[str]:
        path = next((p for p, k in _DOCUMENT_EXPORT_PATHS.items() if k == key), None)
        if not path or not docs.get(key):
            return []
        return [_contents_line(_DOCUMENT_CATALOG_NUMBERS.get(key), path)]

    parts.extend(doc_lines("overview"))
    parts.extend(doc_lines("requirements"))
    parts.extend(doc_lines("options_comparison"))
    if include_mermaid:
        parts.append(_contents_line(4, "diagrams/"))
        diagram_paths = [
            "diagrams/c4-context.mmd",
            "diagrams/c4-container.mmd",
            "diagrams/sequence.mmd",
        ]
        if docs.get("diagram_component"):
            diagram_paths.append("diagrams/c4-component.mmd")
        if docs.get("diagram_dataflow"):
            diagram_paths.append("diagrams/data-flow.mmd")
        parts.extend(f"  - `{p}`" for p in diagram_paths)
    if include_hld:
        parts.append(_contents_line(5, "hld/architecture.md"))
    if include_adrs:
        parts.append(_contents_line(6, "decisions/"))
    if include_risks:
        parts.append(_contents_line(7, "risks/"))
    parts.append(_contents_line(8, "threats/stride-lite.md"))
    parts.append(_contents_line(9, "score/architecture-quality.md"))
    parts.extend(doc_lines("standards_mapping"))
    parts.extend(doc_lines("roadmap"))
    parts.append(_contents_line(12, "backlog/implementation.md"))
    if (package or {}).get("epics"):
        parts.append(_contents_line(13, "backlog/epics-and-stories.md"))
    parts.extend(doc_lines("migration_plan"))
    parts.extend(doc_lines("operational_readiness"))
    parts.extend(doc_lines("cost_model"))
    parts.extend(doc_lines("review_record"))
    parts.extend(doc_lines("traceability"))
    citations = list((package or {}).get("citations") or [])
    if citations:
        parts.append(_contents_line(None, "citations.md"))
    if include_project_json:
        parts.append(_contents_line(None, "project.json"))
    if package and package.get("provenance"):
        parts.extend(
            ["", "## Provenance", "```json", json.dumps(package["provenance"], indent=2), "```"]
        )
    files.append({"path": "README.md", "content": "\n".join(parts) + "\n"})

    for path, key in _DOCUMENT_EXPORT_PATHS.items():
        content = docs.get(key)
        if content:
            files.append({"path": path, "content": content})

    if include_hld and package:
        files.append(
            {
                "path": "hld/architecture.md",
                "content": docs.get("hld") or package["hld_markdown"],
            }
        )
    if include_mermaid and package:
        files.append({"path": "diagrams/c4-context.mmd", "content": package["mermaid"]})
        if package.get("mermaid_container"):
            files.append(
                {
                    "path": "diagrams/c4-container.mmd",
                    "content": package["mermaid_container"],
                }
            )
        if package.get("mermaid_sequence"):
            files.append(
                {"path": "diagrams/sequence.mmd", "content": package["mermaid_sequence"]}
            )
        if docs.get("diagram_component"):
            files.append(
                {
                    "path": "diagrams/c4-component.mmd",
                    "content": docs["diagram_component"],
                }
            )
        if docs.get("diagram_dataflow"):
            files.append(
                {
                    "path": "diagrams/data-flow.mmd",
                    "content": docs["diagram_dataflow"],
                }
            )

    if package:
        from app.modules.options.package_builders import (
            render_adr_markdown,
            render_backlog_markdown,
            render_epics_markdown,
            render_risk_register_markdown,
            render_score_markdown,
            render_threats_markdown,
        )

        if package.get("backlog"):
            files.append(
                {
                    "path": "backlog/implementation.md",
                    "content": render_backlog_markdown(list(package["backlog"])),
                }
            )
        if package.get("epics"):
            files.append(
                {
                    "path": "backlog/epics-and-stories.md",
                    "content": render_epics_markdown(
                        list(package["epics"]),
                        requirements=[
                            str(r) for r in (project.get("requirements") or [])
                        ],
                    ),
                }
            )
        if package.get("threats"):
            files.append(
                {
                    "path": "threats/stride-lite.md",
                    "content": render_threats_markdown(list(package["threats"])),
                }
            )
        if package.get("quality_score"):
            files.append(
                {
                    "path": "score/architecture-quality.md",
                    "content": render_score_markdown(dict(package["quality_score"])),
                }
            )

    if citations:
        cite_lines = [
            "# Citations",
            "",
            f"Retrieval status: `{(package or {}).get('retrieval_status', 'ok')}`",
            "",
        ]
        for c in citations:
            cite_lines.extend(
                [
                    f"## {c.get('citation') or c.get('title')}",
                    "",
                    f"- Source class: {c.get('source_class', '')}",
                    f"- Score: {c.get('score', '')}",
                    "",
                    str(c.get("excerpt") or c.get("text") or ""),
                    "",
                ]
            )
        files.append({"path": "citations.md", "content": "\n".join(cite_lines)})

    if include_adrs:
        from app.modules.options.package_builders import render_adr_markdown

        adrs = list((package or {}).get("adrs") or [])
        opt_title = (selected_option or {}).get("title") or "selected option"
        index_lines = [
            "# Architecture decisions",
            "",
            f"Selected option: **{opt_title}**.",
            "",
        ]
        if not adrs:
            index_lines.append("_No ADRs on this package yet._\n")
        else:
            for adr in adrs:
                aid = str(adr.get("id") or "ADR")
                title = str(adr.get("title") or "Decision")
                fname = f"decisions/{aid}-{_slug(title)}.md"
                index_lines.append(f"- [{aid}: {title}](./{aid}-{_slug(title)}.md)")
                files.append({"path": fname, "content": render_adr_markdown(adr)})
            index_lines.append("")
        files.append({"path": "decisions/README.md", "content": "\n".join(index_lines)})

    if include_risks:
        from app.modules.options.package_builders import render_risk_register_markdown

        risks = list((package or {}).get("risks") or [])
        if not risks:
            files.append(
                {
                    "path": "risks/README.md",
                    "content": "# Risks\n\n_No risks on this package yet._\n",
                }
            )
        else:
            files.append(
                {
                    "path": "risks/register.md",
                    "content": render_risk_register_markdown(risks),
                }
            )
            files.append(
                {
                    "path": "risks/README.md",
                    "content": "# Risks\n\nSee [register.md](./register.md).\n",
                }
            )

    if include_project_json:
        payload = {
            "project": project,
            "selected_option": selected_option,
            "package": (
                {
                    "id": package.get("id"),
                    "status": package.get("status"),
                    "option_id": package.get("option_id"),
                    "provenance": package.get("provenance"),
                    "adrs": package.get("adrs") or [],
                    "risks": package.get("risks") or [],
                    "backlog": package.get("backlog") or [],
                    "epics": package.get("epics") or [],
                    "threats": package.get("threats") or [],
                    "quality_score": package.get("quality_score") or {},
                    "documents": list((package.get("documents") or {}).keys()),
                    "citations": package.get("citations") or [],
                    "retrieval_status": package.get("retrieval_status"),
                }
                if package
                else None
            ),
        }
        files.append(
            {
                "path": "project.json",
                "content": json.dumps(payload, indent=2) + "\n",
            }
        )

    return files
