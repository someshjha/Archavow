"""Package executive-summary assist."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.ai.assist_status import AiAssistStatus, as_ai_failure
from app.ai.gateway import AIGateway
from app.ai.schemas import ChatMessage

if TYPE_CHECKING:
    from app.modules.options.generator import OptionTemplate, ProjectContext

PACKAGE_SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "executive_summary": {"type": "string"},
    },
    "required": ["executive_summary"],
}


def enrich_package_summary(
    gateway: AIGateway,
    ctx: ProjectContext,
    option: OptionTemplate,
    *,
    citation_titles: list[str] | None = None,
) -> tuple[str | None, AiAssistStatus]:
    """Ask chat for a short executive summary. Falls back on error."""
    system = (
        "Write like a working architect, not a brochure. "
        "2–4 plain sentences summarizing the package for a busy peer. "
        "Name the stack and the main trade-off. No buzzwords, no 'leverage', no 'holistic'. "
        "Return JSON only with executive_summary."
    )
    cites = ", ".join(citation_titles or []) or "none"
    user = (
        f"Project: {ctx.name}\n"
        f"Cloud: {ctx.preferred_cloud}\n"
        f"Constraints: {ctx.tech_constraints}\n"
        f"Scale: {ctx.scale_availability}\n"
        f"Selected option: {option.title} — {option.summary}\n"
        f"Stack: {', '.join(option.stack)}\n"
        f"Cited standards: {cites}\n"
    )
    try:
        raw = gateway.complete_json(
            [ChatMessage(role="system", content=system), ChatMessage(role="user", content=user)],
            PACKAGE_SUMMARY_SCHEMA,
            timeout_s=25,
        )
    except Exception as exc:
        return None, as_ai_failure(exc)

    summary = str(raw.get("executive_summary") or "").strip()
    if not summary:
        return None, AiAssistStatus(status="failed", detail="empty_summary")
    return summary, AiAssistStatus(status="ok")
