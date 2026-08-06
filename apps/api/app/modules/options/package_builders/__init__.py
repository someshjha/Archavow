"""Package builders — HLD, diagrams, ADRs, risks, score, backlog, threats.

Split by concern into sibling modules; re-exported here so
`from app.modules.options.package_builders import build_x` keeps working.
"""

from __future__ import annotations

from app.modules.options.package_builders.adrs import build_adrs
from app.modules.options.package_builders.backlog import build_backlog
from app.modules.options.package_builders.diagrams import (
    build_c4_component_mermaid,
    build_c4_container_mermaid,
    build_c4_mermaid,
    build_dataflow_mermaid,
    build_deploy_mermaid,
    build_sequence_mermaid,
)
from app.modules.options.package_builders.documents import (
    MVP_CONDITIONAL,
    MVP_MANDATORY,
    build_package_documents,
)
from app.modules.options.package_builders.epics import build_epics
from app.modules.options.package_builders.hld import build_hld_markdown, build_hld_markdown_ai
from app.modules.options.package_builders.quality_score import (
    SCORE_WEIGHTS,
    build_quality_score,
)
from app.modules.options.package_builders.render import (
    render_adr_markdown,
    render_backlog_markdown,
    render_epics_markdown,
    render_risk_register_markdown,
    render_score_markdown,
    render_threats_markdown,
)
from app.modules.options.package_builders.risks import build_risks
from app.modules.options.package_builders.threats import build_threats

__all__ = [
    "MVP_CONDITIONAL",
    "MVP_MANDATORY",
    "SCORE_WEIGHTS",
    "build_adrs",
    "build_backlog",
    "build_c4_component_mermaid",
    "build_c4_container_mermaid",
    "build_c4_mermaid",
    "build_dataflow_mermaid",
    "build_deploy_mermaid",
    "build_epics",
    "build_hld_markdown",
    "build_hld_markdown_ai",
    "build_package_documents",
    "build_quality_score",
    "build_risks",
    "build_sequence_mermaid",
    "build_threats",
    "render_adr_markdown",
    "render_backlog_markdown",
    "render_epics_markdown",
    "render_risk_register_markdown",
    "render_score_markdown",
    "render_threats_markdown",
]
