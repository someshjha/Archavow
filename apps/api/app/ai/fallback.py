"""Model fallback chain — try each {provider, model} in order until one
succeeds. Used by HLD generation (see app/ai/hld_assist.py) so a mandatory
artifact never goes missing just because one model call failed."""

from __future__ import annotations

from typing import Any, Callable

from app.ai.assist_status import AiAssistStatus, as_ai_failure
from app.ai.gateway import AIGateway
from app.ai.schemas import ChatMessage, ChatModelRef, EffectiveAIConfig


def complete_json_with_fallback(
    chain: list[ChatModelRef],
    messages: list[ChatMessage],
    schema: dict[str, Any],
    *,
    base_config: EffectiveAIConfig,
    gateway_factory: Callable[[EffectiveAIConfig], AIGateway],
    timeout_s: float | None = None,
    is_valid: Callable[[dict[str, Any]], bool] | None = None,
) -> tuple[dict[str, Any] | None, ChatModelRef | None, AiAssistStatus]:
    """Try each chain entry in order; return the first successful JSON result.

    Provider/network failures (see app.ai.assist_status.AI_PROVIDER_ERRORS)
    move on to the next entry. Programming defects still propagate — only
    real provider failures trigger fallback, same as everywhere else in
    this codebase's AI-assist paths.

    `is_valid`, when given, is a quality floor: a successful JSON parse is
    only accepted if `is_valid(result)` is True. A result that fails the
    floor is treated the same as a provider failure for that entry — the
    loop continues to the next chain entry. When `is_valid` is None (the
    default), behavior is unchanged from before this parameter existed.
    """
    if not chain:
        return None, None, AiAssistStatus(status="failed", detail="empty_chain")
    last_status = AiAssistStatus(status="failed", detail="empty_chain")
    for entry in chain:
        # Skip a guaranteed-401 round trip when OpenAI isn't actually configured —
        # same treatment as the is_valid rejection path: record a per-entry
        # failure status and move on to the next chain entry.
        if entry.provider == "openai" and not base_config.openai_api_key_configured:
            last_status = AiAssistStatus(status="failed", detail="openai_key_not_configured")
            continue
        cfg = base_config.model_copy(
            update={"chat_provider": entry.provider, "chat_model": entry.model}
        )
        gateway = gateway_factory(cfg)
        try:
            result = gateway.complete_json(messages, schema, timeout_s=timeout_s)
            if is_valid is not None and not is_valid(result):
                last_status = AiAssistStatus(status="failed", detail="failed_validation")
                continue
            return result, entry, AiAssistStatus(status="ok", detail=f"{entry.provider}/{entry.model}")
        except Exception as exc:
            last_status = as_ai_failure(exc)
            continue
    return None, None, last_status
