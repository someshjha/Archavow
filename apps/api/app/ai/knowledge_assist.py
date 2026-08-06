"""Knowledge Ask / online answer helpers."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.ai.assist import AiAssistStatus, as_ai_failure
from app.ai.gateway import AIGateway
from app.ai.schemas import ChatMessage

KNOWLEDGE_SCORED_ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "score": {"type": "number"},
                    "rationale": {"type": "string"},
                },
                "required": ["id", "score"],
            },
        },
        "answer": {"type": "string"},
        "points": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 6,
        },
        "pattern_name": {"type": ["string", "null"]},
        "mermaid": {"type": ["string", "null"]},
        "confidence": {"type": "number"},
    },
    "required": ["answer", "points", "candidates", "confidence"],
}


ONLINE_ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "points": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 6,
        },
        "pattern_name": {"type": ["string", "null"]},
        "mermaid": {"type": ["string", "null"]},
        "confidence": {"type": "number"},
    },
    "required": ["answer", "points", "confidence"],
}


class KnowledgeAnswer(BaseModel):
    answer: str
    points: list[str] = Field(default_factory=list)
    pattern_name: str | None = None
    mermaid: str | None = None
    confidence: float = 0.0
    source: Literal["knowledge", "model", "web"] = "knowledge"
    status: AiAssistStatus = Field(default_factory=AiAssistStatus)
    best_candidate_score: float = 0.0


def _clean_mermaid(raw: str | None) -> str | None:
    if not raw:
        return None
    text = str(raw).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:mermaid)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    if not text:
        return None
    # Mermaid 11 C4 renames
    text = text.replace("Container_Queue", "ContainerQueue")
    text = text.replace("—", "-").replace("·", "-")
    # Accept common diagram headers
    head = text.splitlines()[0].strip().lower()
    if not any(
        head.startswith(p)
        for p in (
            "flowchart",
            "sequencediagram",
            "classdiagram",
            "statediagram",
            "erdiagram",
            "c4context",
            "c4container",
            "graph ",
            "graph\t",
        )
    ):
        # Still return if it looks like mermaid relations
        if "-->" not in text and "->>" not in text:
            return None
    return text


def compose_scored_knowledge_answer(
    gateway: AIGateway,
    query: str,
    hits: list[Any],
) -> KnowledgeAnswer:
    """Score retrieved excerpts and return the highest-quality crisp answer."""
    if not hits:
        return KnowledgeAnswer(
            answer="",
            status=AiAssistStatus(status="skipped", detail="no_hits"),
            source="knowledge",
        )

    excerpts = []
    for i, h in enumerate(hits[:8], start=1):
        cite = getattr(h, "citation", None) or getattr(h, "title", "source")
        text = getattr(h, "text", "") or ""
        excerpts.append(f"[C{i}] {cite}\n{text[:900]}")
    corpus = "\n\n".join(excerpts)
    messages = [
        ChatMessage(
            role="system",
            content=(
                "Answer like a working architect talking to a peer.\n"
                "Score each excerpt [C1]… for relevance (0-100). Prefer the highest.\n"
                "Plain language — never say seed, corpus, excerpt, or knowledge base.\n"
                "If the question is about a named pattern (CQRS, saga, BFF, etc.), "
                "define it correctly and add a compact Mermaid diagram when it helps.\n"
                "Prefer flowchart LR/TB or sequenceDiagram. For C4 use ContainerQueue "
                "(not Container_Queue). Avoid fancy unicode dashes.\n"
                "answer: 2-5 short sentences. points: up to 6 blunt bullets. "
                "mermaid: valid Mermaid or null. confidence: 0-1. "
                "No brochure words (leverage, robust, seamless)."
            ),
        ),
        ChatMessage(
            role="user",
            content=f"Question:\n{query}\n\nCandidates:\n{corpus}",
        ),
    ]
    try:
        data = gateway.complete_json(messages, schema=KNOWLEDGE_SCORED_ANSWER_SCHEMA)
    except Exception as exc:
        return KnowledgeAnswer(
            answer="",
            status=as_ai_failure(exc),
        )

    answer = str(data.get("answer") or "").strip()
    points = [
        str(p).strip()[:280]
        for p in (data.get("points") or [])
        if str(p).strip()
    ][:6]
    pattern = data.get("pattern_name")
    pattern_name = str(pattern).strip() if pattern else None
    mermaid = _clean_mermaid(data.get("mermaid"))
    try:
        confidence = float(data.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0.0
    best = 0.0
    for c in data.get("candidates") or []:
        try:
            best = max(best, float(c.get("score") or 0) / 100.0)
        except (TypeError, ValueError):
            continue
    if not answer:
        return KnowledgeAnswer(
            answer="",
            status=AiAssistStatus(status="failed", detail="empty_answer"),
        )
    return KnowledgeAnswer(
        answer=answer,
        points=points,
        pattern_name=pattern_name or None,
        mermaid=mermaid,
        confidence=max(0.0, min(1.0, confidence)),
        best_candidate_score=best,
        source="knowledge",
        status=AiAssistStatus(status="ok", detail=f"best={best:.2f}"),
    )


def answer_online_or_model(
    gateway: AIGateway,
    query: str,
) -> KnowledgeAnswer:
    """Fallback when knowledge is weak: prefer live web via OpenAI Responses, else model knowledge."""
    # Try OpenAI Responses + web_search when provider is openai
    if gateway.config.chat_provider == "openai":
        web = _openai_web_answer(gateway, query)
        if web.answer:
            return web

    messages = [
        ChatMessage(
            role="system",
            content=(
                "No strong library hit — answer from solid architecture practice.\n"
                "Talk like a peer. Don't invent org-specific policies.\n"
                "If it's a named pattern, define it and add a small Mermaid diagram when useful.\n"
                "No mentions of AI, seed, or training data. No brochure filler.\n"
                "answer: 2-5 sentences. points: up to 6 bullets. mermaid or null. "
                "confidence 0-1."
            ),
        ),
        ChatMessage(role="user", content=query),
    ]
    try:
        data = gateway.complete_json(messages, schema=ONLINE_ANSWER_SCHEMA)
    except Exception as exc:
        return KnowledgeAnswer(
            answer="",
            status=as_ai_failure(exc),
            source="model",
        )
    answer = str(data.get("answer") or "").strip()
    if not answer:
        return KnowledgeAnswer(
            answer="",
            status=AiAssistStatus(status="failed", detail="empty_online"),
            source="model",
        )
    points = [
        str(p).strip()[:280]
        for p in (data.get("points") or [])
        if str(p).strip()
    ][:6]
    try:
        confidence = float(data.get("confidence") or 0.55)
    except (TypeError, ValueError):
        confidence = 0.55
    pattern = data.get("pattern_name")
    return KnowledgeAnswer(
        answer=answer,
        points=points,
        pattern_name=str(pattern).strip() if pattern else None,
        mermaid=_clean_mermaid(data.get("mermaid")),
        confidence=max(0.0, min(1.0, confidence)),
        source="model",
        status=AiAssistStatus(status="ok", detail="model_fallback"),
    )


def _openai_web_answer(gateway: AIGateway, query: str) -> KnowledgeAnswer:
    """Use OpenAI Responses API with web_search, then structure the result."""
    import json
    import os

    import httpx

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return KnowledgeAnswer(answer="", source="web", status=AiAssistStatus(status="skipped", detail="no_api_key"))

    base = (gateway.config.openai_base_url or "https://api.openai.com/v1").rstrip("/")
    model = gateway.config.chat_model or "gpt-4o-mini"
    prompt = (
        "Answer this software architecture question crisply for a practicing architect. "
        "If it is a pattern, define it correctly. Prefer current industry practice. "
        f"Question: {query}"
    )
    try:
        with httpx.Client(timeout=60.0) as client:
            res = client.post(
                f"{base}/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "tools": [{"type": "web_search"}],
                    "input": prompt,
                },
            )
            if res.status_code >= 400:
                return KnowledgeAnswer(
                    answer="",
                    source="web",
                    status=AiAssistStatus(
                        status="failed", detail=f"responses_{res.status_code}"
                    ),
                )
            payload = res.json()
    except Exception as exc:
        return KnowledgeAnswer(
            answer="",
            source="web",
            status=as_ai_failure(exc),
        )

    # Extract output text from Responses API shape
    text_parts: list[str] = []
    for item in payload.get("output") or []:
        if item.get("type") == "message":
            for part in item.get("content") or []:
                if part.get("type") in {"output_text", "text"} and part.get("text"):
                    text_parts.append(str(part["text"]))
    raw = "\n".join(text_parts).strip() or str(payload.get("output_text") or "").strip()
    if not raw:
        return KnowledgeAnswer(
            answer="",
            source="web",
            status=AiAssistStatus(status="failed", detail="empty_web"),
        )

    # Structure the web prose into our schema
    messages = [
        ChatMessage(
            role="system",
            content=(
                "Rewrite the research notes into a plain architecture answer. "
                "Peer-to-peer tone; no brochure words (leverage, robust, seamless). "
                "Include Mermaid if a pattern diagram helps. "
                "Never mention web search or browsing."
            ),
        ),
        ChatMessage(
            role="user",
            content=f"Question:\n{query}\n\nResearch notes:\n{raw[:6000]}",
        ),
    ]
    try:
        data = gateway.complete_json(messages, schema=ONLINE_ANSWER_SCHEMA)
    except Exception as exc:
        status = as_ai_failure(exc)
        # Fall back to truncated raw text on provider failure
        return KnowledgeAnswer(
            answer=raw[:800],
            points=[],
            confidence=0.5,
            source="web",
            status=AiAssistStatus(status="ok", detail=f"raw_web:{status.detail}"),
        )
    pattern = data.get("pattern_name")
    try:
        confidence = float(data.get("confidence") or 0.65)
    except (TypeError, ValueError):
        confidence = 0.65
    return KnowledgeAnswer(
        answer=str(data.get("answer") or raw[:800]).strip(),
        points=[
            str(p).strip()[:280]
            for p in (data.get("points") or [])
            if str(p).strip()
        ][:6],
        pattern_name=str(pattern).strip() if pattern else None,
        mermaid=_clean_mermaid(data.get("mermaid")),
        confidence=max(0.0, min(1.0, confidence)),
        source="web",
        status=AiAssistStatus(status="ok", detail="web_search"),
    )


# Keep old name as thin wrapper for any external callers
def answer_knowledge_question(
    gateway: AIGateway,
    query: str,
    hits: list[Any],
) -> tuple[str | None, list[str], AiAssistStatus]:
    result = compose_scored_knowledge_answer(gateway, query, hits)
    if not result.answer:
        return None, [], result.status
    return result.answer, result.points, result.status


# Back-compat alias used by older imports/tests
