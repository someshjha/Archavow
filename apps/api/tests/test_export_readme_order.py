"""The export README lists artifacts in MVP catalog order (docs/ARTIFACT_CATALOG.md)."""

from __future__ import annotations

import re

from app.modules.export.packager import build_export_files


def _files(**over):
    package = {
        "documents": {
            "overview": "# Overview",
            "requirements": "# Requirements",
            "options_comparison": "# Options",
            "hld": "# HLD",
            "standards_mapping": "# Standards",
            "roadmap": "# Roadmap",
            "migration_plan": "# Migration",
            "operational_readiness": "# Ops",
            "cost_model": "# Cost",
            "review_record": "# Review",
            "traceability": "# Traceability",
            "diagram_component": "graph TD",
            "diagram_dataflow": "graph LR",
        },
        "hld_markdown": "# HLD",
        "mermaid": "graph TD",
        "mermaid_container": "graph TD",
        "mermaid_sequence": "sequenceDiagram",
        "mermaid_deploy": "graph TD",
        "adrs": [],
        "risks": [],
        "backlog": [],
        "epics": [{"id": "E-001", "title": "Intake", "stories": []}],
        "threats": [],
        "quality_score": {"overall": "partial", "label": "evidence_checklist"},
        "citations": [],
    }
    package.update(over.pop("package", {}))
    kwargs = {
        "include_hld": True,
        "include_mermaid": True,
        "include_adrs": True,
        "include_risks": True,
        "include_project_json": True,
    }
    kwargs.update(over)
    return build_export_files(
        project={"name": "Claims", "requirements": ["Claimants must submit a claim."]},
        package=package,
        selected_option={"title": "Event-driven", "stack": ["Java"]},
        **kwargs,
    )


def _numbers(files: list[dict[str, str]]) -> list[int]:
    readme = next(f for f in files if f["path"] == "README.md")["content"]
    return [int(n) for n in re.findall(r"^- `(\d+)` · `", readme, re.MULTILINE)]


def test_contents_numbers_ascend():
    numbers = _numbers(_files())
    assert numbers, "README listed no numbered artifacts"
    assert numbers == sorted(numbers), numbers


def test_every_catalog_artifact_present_is_numbered_once():
    numbers = _numbers(_files())
    # 1–18; artifact 19 is the package itself. No letter suffixes: the delivery
    # backlog is 13, not "12b".
    assert numbers == list(range(1, 19)), numbers


def test_ordering_holds_when_optional_artifacts_are_absent():
    files = _files(
        package={"epics": [], "documents": {"overview": "# Overview", "roadmap": "# R"}},
        include_adrs=False,
        include_risks=False,
        include_mermaid=False,
    )
    numbers = _numbers(files)
    assert numbers == sorted(numbers), numbers
    assert 13 not in numbers, "no epics, so no delivery backlog entry"
