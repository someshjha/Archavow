"""Strict AI option parsing — fail closed on malformed payloads."""

from __future__ import annotations

from types import SimpleNamespace

from app.ai.assist import (
    _normalize_followup_item,
    generate_architecture_options,
)
from app.modules.options.generator import ProjectContext


class _FakeGateway:
    def __init__(self, payload: dict):
        self._payload = payload
        self.config = SimpleNamespace(chat_provider="none")

    def complete_json(self, messages, schema, *, timeout_s=None):  # noqa: ANN001
        return self._payload


def _ctx() -> ProjectContext:
    return ProjectContext(
        name="Demo",
        business_objective="Cut order latency",
        problem_statement="Checkout spikes drop messages under peak load",
        tech_constraints="Kafka, AKS",
    )


def _design_fields() -> dict:
    return {
        "approach": "Event-driven services with a clear SoR.",
        "assumptions": ["Team can run Kafka day-two"],
        "constraints": ["Stay on evidenced cloud only"],
        "key_decisions": ["Service boundaries vs modular monolith"],
    }


def _valid_options() -> dict:
    base = _design_fields()
    return {
        "options": [
            {
                "key": "rec",
                "title": "Event-driven on AKS",
                "summary": "Streaming path for the checkout problem",
                "pros": ["Scale", "Replay"],
                "cons": ["Ops cost", "Complexity"],
                "fit_score": 90,
                "cost_band": "$$$",
                "ops_band": "high",
                "recommended": True,
                "stack": ["aks", "kafka", "postgres"],
                **base,
            },
            {
                "key": "cheap",
                "title": "Modular monolith",
                "summary": "Simpler ops for moderate peaks",
                "pros": ["Lower ops", "Faster start"],
                "cons": ["Less control", "Cold starts"],
                "fit_score": 70,
                "cost_band": "$$",
                "ops_band": "medium",
                "recommended": False,
                "stack": ["container-apps", "postgres"],
                **base,
            },
            {
                "key": "resilient",
                "title": "Multi-region topology",
                "summary": "HA path when RTO is hard",
                "pros": ["HA", "DR"],
                "cons": ["Cost", "Complexity"],
                "fit_score": 75,
                "cost_band": "$$$$",
                "ops_band": "very high",
                "recommended": False,
                "stack": ["aks", "kafka", "postgres"],
                **base,
            },
        ]
    }


def test_valid_options_parse() -> None:
    opts, status = generate_architecture_options(_FakeGateway(_valid_options()), _ctx())  # type: ignore[arg-type]
    assert status.status == "ok"
    assert len(opts) == 3
    assert sum(1 for o in opts if o.recommended) == 1
    assert opts[0].approach
    assert opts[0].assumptions
    assert opts[0].constraints
    assert opts[0].key_decisions


def test_alias_padded_options_fail_closed() -> None:
    payload = {
        "options": [
            {
                "name": "Alias title",  # wrong key
                "description": "no summary key",
                "advantages": ["a", "b"],
                "disadvantages": ["c", "d"],
                "score": 90,
                "recommended": True,
                "components": ["postgres"],
            },
            {
                "title": "B",
                "summary": "s",
                "pros": ["a", "b"],
                "cons": ["c", "d"],
                "fit_score": 70,
                "cost_band": "$$",
                "ops_band": "medium",
                "recommended": False,
                "stack": ["postgres"],
                "key": "b",
                **_design_fields(),
            },
            {
                "title": "C",
                "summary": "s",
                "pros": ["a", "b"],
                "cons": ["c", "d"],
                "fit_score": 60,
                "cost_band": "$",
                "ops_band": "low",
                "recommended": False,
                "stack": ["postgres"],
                "key": "c",
                **_design_fields(),
            },
        ]
    }
    opts, status = generate_architecture_options(_FakeGateway(payload), _ctx())  # type: ignore[arg-type]
    assert opts == []
    assert status.status == "failed"


def test_fabricated_defaults_not_applied() -> None:
    payload = {
        "options": [
            {
                "key": "a",
                "title": "Only one pro",
                "summary": "s",
                "pros": ["one"],
                "cons": ["c", "d"],
                "fit_score": 90,
                "cost_band": "$$$",
                "ops_band": "high",
                "recommended": True,
                "stack": ["aks"],
                **_design_fields(),
            },
            {
                "key": "b",
                "title": "B",
                "summary": "s",
                "pros": ["a", "b"],
                "cons": ["c", "d"],
                "fit_score": 70,
                "cost_band": "$$",
                "ops_band": "medium",
                "recommended": False,
                "stack": ["postgres"],
                **_design_fields(),
            },
            {
                "key": "c",
                "title": "C",
                "summary": "s",
                "pros": ["a", "b"],
                "cons": ["c", "d"],
                "fit_score": 60,
                "cost_band": "$",
                "ops_band": "low",
                "recommended": False,
                "stack": ["postgres"],
                **_design_fields(),
            },
        ]
    }
    opts, status = generate_architecture_options(_FakeGateway(payload), _ctx())  # type: ignore[arg-type]
    assert opts == []
    assert status.status == "failed"
    assert "incomplete" in (status.detail or "")


def test_missing_design_fields_fail_closed() -> None:
    payload = _valid_options()
    del payload["options"][0]["assumptions"]
    opts, status = generate_architecture_options(_FakeGateway(payload), _ctx())  # type: ignore[arg-type]
    assert opts == []
    assert status.status == "failed"


def test_followup_normalizer_rejects_bad_category() -> None:
    assert (
        _normalize_followup_item(
            {"code": "ai_x", "prompt": "What about auth?", "category": "random"},
            existing=set(),
        )
        is None
    )
    gap = _normalize_followup_item(
        {"code": "ai_y", "prompt": "What about auth?", "category": "security"},
        existing=set(),
    )
    assert gap is not None
    assert gap.category == "security"
