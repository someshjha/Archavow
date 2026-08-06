"""Structured Outputs: schema adaptation and provider request shape.

Regression cover for the bug where the schema was accepted by complete_json and
never sent, so the model renamed fields (stack -> stack_tags) and returned strings
where arrays were required. Every AI option set was then rejected as incomplete
and silently replaced by deterministic templates.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.ai.assist_options import OPTIONS_SCHEMA
from app.ai.json_schema import UnsupportedSchemaError, to_strict_schema
from app.ai.providers.openai_chat import OpenAIChatProvider, OpenAIRefusalError
from app.ai.schemas import ChatMessage


_REAL_CLIENT = httpx.Client


def _mock_http(monkeypatch, handler) -> None:
    """Route the provider's httpx.Client through a MockTransport."""

    def factory(**kwargs):
        kwargs.pop("transport", None)
        return _REAL_CLIENT(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(httpx, "Client", factory)


# --- adapter ---------------------------------------------------------------


def test_every_object_gets_additional_properties_false() -> None:
    strict = to_strict_schema(
        {
            "type": "object",
            "properties": {
                "outer": {
                    "type": "object",
                    "properties": {"inner": {"type": "string"}},
                }
            },
        }
    )
    assert strict["additionalProperties"] is False
    assert strict["properties"]["outer"]["additionalProperties"] is False


def test_all_declared_properties_become_required() -> None:
    strict = to_strict_schema(
        {
            "type": "object",
            "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
            "required": ["a"],
        }
    )
    assert sorted(strict["required"]) == ["a", "b"]
    # Optional non-nullable `b` becomes required+nullable so omit → null on the wire.
    assert strict["properties"]["a"]["type"] == "string"
    assert strict["properties"]["b"]["type"] == ["string", "null"]


def test_already_nullable_optional_stays_nullable() -> None:
    strict = to_strict_schema(
        {
            "type": "object",
            "properties": {
                "note": {"type": ["string", "null"]},
                "must": {"type": "string"},
            },
            "required": ["must"],
        }
    )
    assert sorted(strict["required"]) == ["must", "note"]
    assert strict["properties"]["note"]["type"] == ["string", "null"]
    assert strict["properties"]["must"]["type"] == "string"


def test_post_validate_treats_null_optional_as_omitted() -> None:
    from app.ai.json_schema import validate_against_schema

    schema = {
        "type": "object",
        "properties": {
            "must": {"type": "string"},
            "maybe": {"type": "string"},
        },
        "required": ["must"],
    }
    # Wire form may send null for optional keys; contract treats that as omit.
    out = validate_against_schema({"must": "x", "maybe": None}, schema)
    assert out == {"must": "x"}
    assert "maybe" not in out


def test_gateway_returns_normalized_optional_nulls() -> None:
    from app.ai.gateway import AIGateway
    from app.ai.schemas import EffectiveAIConfig
    from tests.fakes import FakeChatProvider, FakeEmbeddingProvider

    schema = {
        "type": "object",
        "properties": {
            "must": {"type": "string"},
            "maybe": {"type": "string"},
        },
        "required": ["must"],
    }
    chat = FakeChatProvider(json_response={"must": "ok", "maybe": None})
    gw = AIGateway(EffectiveAIConfig(), chat, FakeEmbeddingProvider())
    assert gw.complete_json([ChatMessage(role="user", content="hi")], schema) == {
        "must": "ok"
    }


def test_post_validate_rejects_null_for_required_field() -> None:
    from app.ai.json_schema import SchemaValidationError, validate_against_schema

    schema = {
        "type": "object",
        "properties": {"must": {"type": "string"}},
        "required": ["must"],
    }
    with pytest.raises(SchemaValidationError):
        validate_against_schema({"must": None}, schema)


def test_post_validate_rejects_invalid_schema_document() -> None:
    from app.ai.json_schema import SchemaValidationError, validate_against_schema

    with pytest.raises(SchemaValidationError, match="invalid schema"):
        validate_against_schema({"a": 1}, {"type": "object", "required": "not-a-list"})


def test_array_item_objects_are_adapted() -> None:
    strict = to_strict_schema(
        {
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"x": {"type": "string"}},
                    },
                }
            },
        }
    )
    item = strict["properties"]["rows"]["items"]
    assert item["additionalProperties"] is False
    assert item["required"] == ["x"]


def test_nullable_object_is_adapted() -> None:
    strict = to_strict_schema(
        {
            "type": "object",
            "properties": {
                "followup": {
                    "type": ["object", "null"],
                    "properties": {"code": {"type": "string"}},
                }
            },
        }
    )
    followup = strict["properties"]["followup"]
    assert followup["additionalProperties"] is False
    assert followup["required"] == ["code"]


def test_unsupported_validation_keywords_are_dropped() -> None:
    strict = to_strict_schema(
        {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 1, "maximum": 100},
                "name": {"type": "string", "pattern": "^a", "minLength": 2},
            },
        }
    )
    assert "minimum" not in strict["properties"]["score"]
    assert "maximum" not in strict["properties"]["score"]
    assert "pattern" not in strict["properties"]["name"]
    assert "minLength" not in strict["properties"]["name"]


def test_post_validate_rejects_out_of_range_against_original_schema() -> None:
    from app.ai.json_schema import SchemaValidationError, validate_against_schema

    schema = {
        "type": "object",
        "properties": {
            "fit_score": {"type": "integer", "minimum": 1, "maximum": 100},
        },
        "required": ["fit_score"],
    }
    validate_against_schema({"fit_score": 50}, schema)
    with pytest.raises(SchemaValidationError):
        validate_against_schema({"fit_score": 999}, schema)


def test_post_validate_rejects_additional_properties() -> None:
    from app.ai.json_schema import SchemaValidationError, validate_against_schema

    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
        "additionalProperties": False,
    }
    validate_against_schema({"name": "ok"}, schema)
    with pytest.raises(SchemaValidationError, match="[Aa]dditional"):
        validate_against_schema({"name": "ok", "extra": 1}, schema)


def test_post_validate_rejects_enum_and_one_of() -> None:
    from app.ai.json_schema import SchemaValidationError, validate_against_schema

    enum_schema = {
        "type": "object",
        "properties": {"tier": {"type": "string", "enum": ["a", "b"]}},
        "required": ["tier"],
    }
    validate_against_schema({"tier": "a"}, enum_schema)
    with pytest.raises(SchemaValidationError):
        validate_against_schema({"tier": "c"}, enum_schema)

    one_of_schema = {
        "type": "object",
        "properties": {
            "value": {
                "oneOf": [
                    {"type": "string", "minLength": 1},
                    {"type": "integer", "minimum": 0},
                ]
            }
        },
        "required": ["value"],
    }
    validate_against_schema({"value": "x"}, one_of_schema)
    validate_against_schema({"value": 2}, one_of_schema)
    with pytest.raises(SchemaValidationError):
        validate_against_schema({"value": -1}, one_of_schema)


def test_post_validate_rejects_exclusive_bounds_and_format() -> None:
    from app.ai.json_schema import SchemaValidationError, validate_against_schema

    bounds = {
        "type": "object",
        "properties": {
            "n": {"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 1},
        },
        "required": ["n"],
    }
    validate_against_schema({"n": 0.5}, bounds)
    with pytest.raises(SchemaValidationError):
        validate_against_schema({"n": 0}, bounds)
    with pytest.raises(SchemaValidationError):
        validate_against_schema({"n": 1}, bounds)

    fmt = {
        "type": "object",
        "properties": {"email": {"type": "string", "format": "email"}},
        "required": ["email"],
    }
    validate_against_schema({"email": "a@b.co"}, fmt)
    with pytest.raises(SchemaValidationError):
        validate_against_schema({"email": "not-an-email"}, fmt)


def test_gateway_post_validates_original_schema() -> None:
    from app.ai.gateway import AIGateway
    from app.ai.json_schema import SchemaValidationError
    from app.ai.schemas import EffectiveAIConfig
    from tests.fakes import FakeChatProvider, FakeEmbeddingProvider

    schema = {
        "type": "object",
        "properties": {"fit_score": {"type": "integer", "minimum": 1, "maximum": 100}},
        "required": ["fit_score"],
    }
    chat = FakeChatProvider(json_response={"fit_score": 999})
    gw = AIGateway(EffectiveAIConfig(), chat, FakeEmbeddingProvider())
    with pytest.raises(SchemaValidationError):
        gw.complete_json([ChatMessage(role="user", content="hi")], schema)


def test_item_count_bounds_are_preserved() -> None:
    strict = to_strict_schema(
        {
            "type": "object",
            "properties": {
                "options": {"type": "array", "minItems": 3, "maxItems": 3},
            },
        }
    )
    assert strict["properties"]["options"]["minItems"] == 3
    assert strict["properties"]["options"]["maxItems"] == 3


def test_open_ended_map_is_rejected_not_mangled() -> None:
    """Forcing additionalProperties:false here would permit zero keys."""
    with pytest.raises(UnsupportedSchemaError):
        to_strict_schema(
            {
                "type": "object",
                "properties": {
                    "rewrites": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    }
                },
            }
        )


def test_options_schema_is_strict_ready() -> None:
    strict = to_strict_schema(OPTIONS_SCHEMA)
    item = strict["properties"]["options"]["items"]
    assert item["additionalProperties"] is False
    assert "stack" in item["required"]
    for field in ("assumptions", "constraints", "key_decisions"):
        assert item["properties"][field]["type"] == "array"
        assert field in item["required"]


def test_adapter_does_not_mutate_input() -> None:
    original = json.dumps(OPTIONS_SCHEMA, sort_keys=True)
    to_strict_schema(OPTIONS_SCHEMA)
    assert json.dumps(OPTIONS_SCHEMA, sort_keys=True) == original


# --- provider request shape ------------------------------------------------


def test_provider_sends_strict_json_schema(monkeypatch) -> None:
    sent: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"options": []}'}}]},
        )

    provider = OpenAIChatProvider(api_key="k", model="gpt-4o-mini")
    _mock_http(monkeypatch, handler)
    provider.complete_json([ChatMessage(role="user", content="hi")], OPTIONS_SCHEMA)

    fmt = sent["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["strict"] is True
    item = fmt["json_schema"]["schema"]["properties"]["options"]["items"]
    assert "stack" in item["required"]


def test_provider_downgrades_when_endpoint_rejects_schema(monkeypatch) -> None:
    formats: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        formats.append(body["response_format"]["type"])
        if body["response_format"]["type"] == "json_schema":
            return httpx.Response(
                400,
                json={"error": {"message": "Invalid parameter", "param": "response_format"}},
            )
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"ok": 1}'}}]})

    provider = OpenAIChatProvider(api_key="k", model="legacy-model")
    _mock_http(monkeypatch, handler)
    out = provider.complete_json([ChatMessage(role="user", content="hi")], OPTIONS_SCHEMA)

    assert formats == ["json_schema", "json_object"]
    assert out == {"ok": 1}


def test_provider_uses_json_object_for_open_ended_map_schema(monkeypatch) -> None:
    from app.ai.assist_interview import INTERVIEW_ASSIST_SCHEMA

    sent: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    provider = OpenAIChatProvider(api_key="k", model="gpt-4o-mini")
    _mock_http(monkeypatch, handler)
    provider.complete_json([ChatMessage(role="user", content="hi")], INTERVIEW_ASSIST_SCHEMA)

    assert sent["response_format"] == {"type": "json_object"}


def test_provider_raises_on_refusal(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"refusal": "I cannot help with that."}}]},
        )

    provider = OpenAIChatProvider(api_key="k", model="gpt-4o-mini")
    _mock_http(monkeypatch, handler)
    with pytest.raises(OpenAIRefusalError):
        provider.complete_json([ChatMessage(role="user", content="hi")], OPTIONS_SCHEMA)


def test_provider_still_raises_on_non_schema_400(monkeypatch) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append("x")
        return httpx.Response(400, json={"error": {"message": "quota exceeded"}})

    provider = OpenAIChatProvider(api_key="k", model="gpt-4o-mini")
    _mock_http(monkeypatch, handler)
    with pytest.raises(httpx.HTTPStatusError):
        provider.complete_json([ChatMessage(role="user", content="hi")], OPTIONS_SCHEMA)
    assert len(calls) == 1
