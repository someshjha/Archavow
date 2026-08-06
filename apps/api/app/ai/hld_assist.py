"""HLD structured content — AI-grounded, with the deterministic markdown in
package_builders/hld.py as the guaranteed fallback when every model fails."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from app.ai.assist_status import AiAssistStatus
from app.ai.fallback import complete_json_with_fallback
from app.ai.gateway import AIGateway
from app.ai.schemas import ChatMessage, ChatModelRef, EffectiveAIConfig

if TYPE_CHECKING:
    from app.modules.options.generator import OptionTemplate, ProjectContext

HLD_CONTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "component_responsibilities": {"type": "array", "items": {"type": "string"}},
        "technology_choices": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "area": {"type": "string"},
                    "technology": {"type": "string"},
                    "why": {"type": "string"},
                },
                "required": ["area", "technology", "why"],
            },
        },
        "integration_patterns": {"type": "array", "items": {"type": "string"}},
        "data_ownership": {"type": "array", "items": {"type": "string"}},
        "api_event_boundaries": {"type": "array", "items": {"type": "string"}},
        "scaling_availability": {"type": "array", "items": {"type": "string"}},
        "failure_handling": {"type": "array", "items": {"type": "string"}},
        "assumptions": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "component_responsibilities",
        "technology_choices",
        "integration_patterns",
        "data_ownership",
        "api_event_boundaries",
        "scaling_availability",
        "failure_handling",
        "assumptions",
    ],
}

# The 7 rendered sections that must each carry real content for an AI response
# to be accepted over the deterministic template. `assumptions` is deliberately
# excluded — it's fine for a model to have nothing to flag there.
_REQUIRED_NON_EMPTY_KEYS = (
    "component_responsibilities",
    "technology_choices",
    "integration_patterns",
    "data_ownership",
    "api_event_boundaries",
    "scaling_availability",
    "failure_handling",
)


def _is_valid_hld_content(result: dict[str, Any]) -> bool:
    """Quality floor: reject a response where any of the 7 rendered sections
    is missing, non-list, or empty — that's a worse artifact than the
    deterministic template, so it should not "win" over it."""
    return all(
        isinstance(result.get(key), list) and len(result[key]) > 0
        for key in _REQUIRED_NON_EMPTY_KEYS
    )


def generate_hld_content(
    ctx: ProjectContext,
    option: OptionTemplate,
    *,
    citations: list[dict] | None,
    fallback_chain: list[ChatModelRef],
    base_config: EffectiveAIConfig,
    gateway_factory: Callable[[EffectiveAIConfig], AIGateway],
) -> tuple[dict[str, Any] | None, ChatModelRef | None, AiAssistStatus]:
    """Structured HLD sub-sections, grounded in project context + retrieved
    past decisions. Returns (content, model_used, status); content is None
    only when every model in fallback_chain fails."""
    cite_lines = (
        "\n".join(
            f"- [{c.get('source_class', 'org')}] "
            f"{c.get('citation', c.get('title', 'reference'))}: "
            f"{(c.get('excerpt') or c.get('text') or '')[:200]}"
            for c in (citations or [])
        )
        or "- (none retrieved)"
    )
    reqs = "\n".join(f"- {r}" for r in ctx.requirements) or "- (nothing captured yet)"
    system = (
        "You are Archavow's high-level-design copilot. Produce the structured "
        "content for a High-Level Design document's technical sections. Return JSON only.\n"
        "Every claim must trace to the project context, the requirements below, or a "
        "cited reference — name specific technologies/products where the context "
        "supports it, never generic categories like 'a modern database'. "
        "If something must be assumed rather than stated, put it in `assumptions`, "
        "not asserted as fact elsewhere. No boilerplate phrases such as "
        "'consider scalability' or 'ensure security best practices' — every bullet "
        "must be a concrete, specific statement about THIS system."
    )
    user = (
        f"System: {ctx.name}\n"
        f"Objective: {ctx.business_objective or '—'}\n"
        f"Problem: {ctx.problem_statement or '—'}\n"
        f"Cloud: {ctx.preferred_cloud or '—'}\n"
        f"Constraints: {ctx.tech_constraints or '—'}\n"
        f"Scale: {ctx.scale_availability or '—'}\n"
        f"Selected option: {option.title} — {option.summary}\n"
        f"Stack: {', '.join(option.stack) or 'still open'}\n"
        f"Cost/ops bands: {option.cost_band} / {option.ops_band}\n\n"
        f"Requirements captured so far (from intake + interview):\n{reqs}\n\n"
        f"Retrieved reference material from past Archavow decisions:\n{cite_lines}\n"
    )
    messages = [
        ChatMessage(role="system", content=system),
        ChatMessage(role="user", content=user),
    ]
    return complete_json_with_fallback(
        fallback_chain,
        messages,
        HLD_CONTENT_SCHEMA,
        base_config=base_config,
        gateway_factory=gateway_factory,
        timeout_s=25,
        is_valid=_is_valid_hld_content,
    )
