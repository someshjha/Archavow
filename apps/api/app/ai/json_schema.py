"""Adapt hand-written JSON schemas for OpenAI Structured Outputs (strict mode).

Strict mode rejects a schema unless every object sets ``additionalProperties: false``
and lists *all* of its properties in ``required``. Our call-site schemas are written
for readability, so they are adapted here instead of duplicating strict boilerplate
in every assist module.

``to_strict_schema`` is a **wire format** for the provider only — it is not the
contract. Optional non-nullable properties become required + nullable on the wire
(null stands in for omit). Call sites must keep validating responses against the
original schema via ``validate_against_schema`` (see ``AIGateway.complete_json``),
which uses the ``jsonschema`` library (Draft 2020-12 + format checking) and treats
null optional fields as omitted.
"""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

# Validation-only keywords strict mode refuses outright. Ranges such as fit_score
# 1-100 are enforced by validate_against_schema after the response lands.
_UNSUPPORTED_KEYWORDS = frozenset(
    {
        "allOf",
        "not",
        "dependentRequired",
        "dependentSchemas",
        "if",
        "then",
        "else",
        "patternProperties",
        "unevaluatedProperties",
        "unevaluatedItems",
        "propertyNames",
        "minLength",
        "maxLength",
        "pattern",
        "format",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "default",
    }
)


class UnsupportedSchemaError(ValueError):
    """Schema cannot be expressed in strict mode and must not be silently altered."""


class SchemaValidationError(ValueError):
    """Model JSON failed the original (pre-strict) schema contract."""


def to_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of ``schema`` accepted by ``strict: true``.

    Every object gets ``additionalProperties: false`` and a ``required`` list
    covering all declared properties. Optional properties that were not nullable
    become nullable so the model can send ``null`` instead of omitting the key.
    Unsupported validation keywords are dropped.

    Raises ``UnsupportedSchemaError`` for shapes strict mode cannot express, so
    the caller can keep the looser request format rather than send a schema whose
    meaning changed. The notable case is an open-ended map
    (``additionalProperties`` holding a schema), which strict mode forbids
    outright — forcing it to ``false`` would allow zero keys and quietly gut the
    contract.
    """
    adapted = _adapt(schema)
    if not isinstance(adapted, dict):
        raise UnsupportedSchemaError("root schema must be an object")
    return adapted


def validate_against_schema(instance: Any, schema: dict[str, Any]) -> Any:
    """Enforce the original call-site schema with Draft 2020-12 + format checking.

    Returns a normalized copy where null values on optional properties are
    dropped (matching the strict-wire nullable stand-in for omit). Callers such
    as ``AIGateway.complete_json`` must return this object, not the raw provider
    payload.

    Raises ``SchemaValidationError`` when the instance is invalid, or when the
    schema itself is not a valid JSON Schema.
    """
    try:
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(
            schema,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )
        normalized = _drop_null_optionals(instance, schema)
        errors = sorted(
            validator.iter_errors(normalized),
            key=lambda e: list(e.absolute_path),
        )
    except SchemaError as exc:
        raise SchemaValidationError(f"invalid schema: {exc.message}") from exc

    if errors:
        messages: list[str] = []
        for err in errors[:8]:
            path = "$"
            if err.absolute_path:
                path = "$." + ".".join(str(p) for p in err.absolute_path)
            messages.append(f"{path}: {err.message}")
        raise SchemaValidationError("; ".join(messages))

    return normalized


def _adapt(node: Any) -> Any:
    if isinstance(node, list):
        return [_adapt(item) for item in node]
    if not isinstance(node, dict):
        return node

    if isinstance(node.get("additionalProperties"), dict):
        raise UnsupportedSchemaError("open-ended maps are not supported in strict mode")

    # Capture original required before recursion so optionals stay identifiable.
    original_required = {
        str(x) for x in (node.get("required") or []) if isinstance(x, str)
    }

    out: dict[str, Any] = {}
    for key, value in node.items():
        if key in _UNSUPPORTED_KEYWORDS:
            continue
        if key in {"properties", "$defs", "definitions"} and isinstance(value, dict):
            out[key] = {k: _adapt(v) for k, v in value.items()}
        elif key in {"anyOf", "oneOf"} and isinstance(value, list):
            out[key] = [_adapt(v) for v in value]
        elif key in {"items", "additionalProperties", "contains"}:
            out[key] = _adapt(value)
        else:
            out[key] = _adapt(value)

    if _is_object_schema(out):
        props = out.get("properties")
        prop_names = list(props.keys()) if isinstance(props, dict) else []
        if isinstance(props, dict):
            for name, prop_schema in list(props.items()):
                if name not in original_required and isinstance(prop_schema, dict):
                    props[name] = _as_nullable(prop_schema)
        out["additionalProperties"] = False
        # Strict mode has no notion of an optional key: every declared property
        # must be required. Formerly-optional fields are nullable so null ≈ omit.
        out["required"] = prop_names
    return out


def _is_nullable(schema: dict[str, Any]) -> bool:
    node_type = schema.get("type")
    if node_type == "null":
        return True
    if isinstance(node_type, list) and "null" in node_type:
        return True
    for key in ("anyOf", "oneOf"):
        alts = schema.get(key)
        if isinstance(alts, list) and any(
            isinstance(a, dict) and a.get("type") == "null" for a in alts
        ):
            return True
    return False


def _as_nullable(schema: dict[str, Any]) -> dict[str, Any]:
    if _is_nullable(schema):
        return schema
    node_type = schema.get("type")
    if isinstance(node_type, str):
        return {**schema, "type": [node_type, "null"]}
    if isinstance(node_type, list):
        return {**schema, "type": [*node_type, "null"]}
    # No type keyword — wrap so null is an allowed alternative without rewriting.
    return {"anyOf": [schema, {"type": "null"}]}


def _drop_null_optionals(instance: Any, schema: dict[str, Any]) -> Any:
    """Drop nulls on optional properties so wire nulls match omit semantics."""
    if not isinstance(instance, dict) or not isinstance(schema, dict):
        return instance
    props = schema.get("properties")
    if not isinstance(props, dict):
        return instance
    required = {str(x) for x in (schema.get("required") or []) if isinstance(x, str)}
    out: dict[str, Any] = {}
    for key, value in instance.items():
        if key not in required and value is None and key in props:
            continue
        child_schema = props.get(key)
        if isinstance(value, dict) and isinstance(child_schema, dict):
            out[key] = _drop_null_optionals(value, child_schema)
        elif isinstance(value, list) and isinstance(child_schema, dict):
            items = child_schema.get("items")
            if isinstance(items, dict):
                out[key] = [
                    _drop_null_optionals(item, items) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                out[key] = value
        else:
            out[key] = value
    return out


def _is_object_schema(node: dict[str, Any]) -> bool:
    node_type = node.get("type")
    if node_type == "object":
        return True
    # Nullable objects are declared as {"type": ["object", "null"]}.
    if isinstance(node_type, list) and "object" in node_type:
        return True
    return "properties" in node and node_type is None
