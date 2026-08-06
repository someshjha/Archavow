"""Architecture options generation assist — solution approaches, not deploy variants."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.ai.assist_status import AiAssistStatus, as_ai_failure
from app.ai.gateway import AIGateway
from app.ai.schemas import ChatMessage

if TYPE_CHECKING:
    from app.modules.options.generator import ProjectContext

OPTIONS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "options": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "approach": {"type": "string"},
                    "assumptions": {"type": "array", "items": {"type": "string"}},
                    "constraints": {"type": "array", "items": {"type": "string"}},
                    "key_decisions": {"type": "array", "items": {"type": "string"}},
                    "pros": {"type": "array", "items": {"type": "string"}},
                    "cons": {"type": "array", "items": {"type": "string"}},
                    "fit_score": {"type": "integer"},
                    "cost_band": {"type": "string"},
                    "ops_band": {"type": "string"},
                    "recommended": {"type": "boolean"},
                    "stack": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "key",
                    "title",
                    "summary",
                    "approach",
                    "assumptions",
                    "constraints",
                    "key_decisions",
                    "pros",
                    "cons",
                    "fit_score",
                    "cost_band",
                    "ops_band",
                    "recommended",
                    "stack",
                ],
            },
        }
    },
    "required": ["options"],
}


def _str_list(value: Any, *, min_n: int = 0, max_n: int = 8) -> list[str] | None:
    if not isinstance(value, list):
        return None
    out = [str(x).strip() for x in value if str(x).strip()]
    if len(out) < min_n:
        return None
    return out[:max_n]


def generate_architecture_options(
    gateway: AIGateway,
    ctx: ProjectContext,
) -> tuple[list[Any], AiAssistStatus]:
    """Ask chat for exactly 3 distinct solution approaches. Fail closed on invalid shape."""
    from app.modules.options.generator import OptionTemplate

    system = (
        "You are a solution architect. Return JSON ONLY.\n"
        "Produce exactly 3 DISTINCT architecture OPTIONS for solving the stated problem — "
        "not three flavors of the same deployment (e.g. not Kafka vs Redpanda vs Kafka-HA).\n"
        "Each option must differ in solution shape, for example: modular monolith vs "
        "event-driven services vs strangler/incremental extraction vs CQRS/read-optimized, "
        "or different integration/data ownership boundaries that matter for THIS problem.\n"
        "Ground every option in the objective, problem statement, and captured requirements. "
        "Do not invent a cloud, language, or broker that is not evidenced in the project context.\n"
        "For each option include:\n"
        "- approach: 2-4 sentences on how the system works end-to-end for this problem\n"
        "- assumptions: what must be true (explicit)\n"
        "- constraints: design constraints this option respects or imposes\n"
        "- key_decisions: contested choices an ADR would capture\n"
        "- pros/cons (>=2 each), fit_score 1-100, cost_band, ops_band, stack tags\n"
        "Exactly one recommended=true. Write like a colleague: concrete, short, no brochure words."
    )
    user = (
        f"Project: {ctx.name}\n"
        f"Objective: {ctx.business_objective or '—'}\n"
        f"Problem: {ctx.problem_statement or '—'}\n"
        f"Cloud: {ctx.preferred_cloud or '—'}\n"
        f"Scale / availability: {ctx.scale_availability or '—'}\n"
        f"Tech constraints: {ctx.tech_constraints or '—'}\n"
        f"Captured requirements / interview answers:\n"
        + ("\n".join(f"- {r}" for r in ctx.requirements[:20]) or "- (none yet)")
        + "\n\nReturn 3 real solution approaches tailored to this problem."
    )
    try:
        raw = gateway.complete_json(
            [ChatMessage(role="system", content=system), ChatMessage(role="user", content=user)],
            OPTIONS_SCHEMA,
            timeout_s=90,
        )
    except Exception as exc:
        return [], as_ai_failure(exc)

    items = raw.get("options")
    if not isinstance(items, list) or len(items) != 3:
        return [], AiAssistStatus(status="failed", detail="need_exactly_three_options")

    def _stack_tokens(value: Any) -> list[str] | None:
        if not isinstance(value, list) or not value:
            return None
        out: list[str] = []
        for s in value:
            tok = str(s).strip().lower().replace(" ", "-")
            if tok:
                out.append(tok[:48])
        return out[:8] if out else None

    out: list[OptionTemplate] = []
    seen_keys: set[str] = set()
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            return [], AiAssistStatus(status="failed", detail=f"option_{idx}_not_object")
        title = str(item.get("title") or "").strip()
        summary = str(item.get("summary") or "").strip()
        approach = str(item.get("approach") or "").strip()
        pros = _str_list(item.get("pros"), min_n=2, max_n=6)
        cons = _str_list(item.get("cons"), min_n=2, max_n=6)
        assumptions = _str_list(item.get("assumptions"), min_n=1, max_n=8)
        constraints = _str_list(item.get("constraints"), min_n=1, max_n=8)
        key_decisions = _str_list(item.get("key_decisions"), min_n=1, max_n=8)
        stack = _stack_tokens(item.get("stack"))
        key = str(item.get("key") or "").strip().replace(" ", "_").lower()[:64]
        if (
            not title
            or not summary
            or not approach
            or pros is None
            or cons is None
            or assumptions is None
            or constraints is None
            or key_decisions is None
            or not stack
            or not key
        ):
            return [], AiAssistStatus(status="failed", detail=f"option_{idx}_incomplete")
        if key in seen_keys:
            return [], AiAssistStatus(status="failed", detail=f"option_{idx}_duplicate_key")
        seen_keys.add(key)
        try:
            fit_i = max(1, min(100, int(item.get("fit_score"))))
        except (TypeError, ValueError):
            return [], AiAssistStatus(status="failed", detail=f"option_{idx}_bad_fit_score")
        if "recommended" not in item or not isinstance(item.get("recommended"), bool):
            return [], AiAssistStatus(status="failed", detail=f"option_{idx}_bad_recommended")
        cost_band = str(item.get("cost_band") or "").strip()
        ops_band = str(item.get("ops_band") or "").strip()
        if not cost_band or not ops_band:
            return [], AiAssistStatus(status="failed", detail=f"option_{idx}_bad_bands")
        try:
            tmpl = OptionTemplate(
                key=key,
                title=title,
                summary=summary,
                approach=approach,
                assumptions=assumptions,
                constraints=constraints,
                key_decisions=key_decisions,
                pros=pros,
                cons=cons,
                fit_score=fit_i,
                cost_band=cost_band[:16],
                ops_band=ops_band[:32],
                recommended=bool(item["recommended"]),
                stack=stack,
                origin="ai",
            )
        except ValueError as exc:
            return [], AiAssistStatus(status="failed", detail=str(exc)[:180])
        out.append(tmpl)

    rec_count = sum(1 for o in out if o.recommended)
    if rec_count != 1:
        return [], AiAssistStatus(status="failed", detail=f"recommended_count={rec_count}")

    return out, AiAssistStatus(status="ok", detail="options=3")
