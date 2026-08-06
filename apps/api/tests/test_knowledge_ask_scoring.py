"""Unit tests for scored knowledge answers + Mermaid cleaning."""

from __future__ import annotations

from types import SimpleNamespace

from app.ai.knowledge_assist import _clean_mermaid, compose_scored_knowledge_answer


def test_clean_mermaid_strips_fences() -> None:
    raw = "```mermaid\nflowchart LR\n  A-->B\n```"
    cleaned = _clean_mermaid(raw)
    assert cleaned is not None
    assert "flowchart" in cleaned
    assert "```" not in cleaned


def test_compose_scored_picks_highest_and_keeps_professional_language() -> None:
    gw = SimpleNamespace(
        complete_json=lambda messages, schema: {
            "candidates": [
                {"id": "C1", "score": 40, "rationale": "weak"},
                {"id": "C2", "score": 92, "rationale": "best"},
            ],
            "answer": (
                "CQRS separates the write model from the read model so each can "
                "scale and evolve independently."
            ),
            "points": [
                "Commands mutate the write side",
                "Queries serve denormalized read models",
            ],
            "pattern_name": "CQRS",
            "mermaid": "flowchart LR\n  Client-->CommandAPI\n  Client-->QueryAPI",
            "confidence": 0.88,
        }
    )
    hits = [
        SimpleNamespace(
            citation="Industry › CQRS",
            title="CQRS",
            text="CQRS is Command Query Responsibility Segregation.",
        )
    ]
    result = compose_scored_knowledge_answer(gw, "What is CQRS?", hits)  # type: ignore[arg-type]
    assert result.status.status == "ok"
    assert result.best_candidate_score == 0.92
    assert result.pattern_name == "CQRS"
    assert result.mermaid and "flowchart" in result.mermaid
    assert "seed" not in result.answer.lower()
    assert result.confidence == 0.88
