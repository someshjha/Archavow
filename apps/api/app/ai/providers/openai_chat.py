"""OpenAI chat provider."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.ai.json_schema import UnsupportedSchemaError, to_strict_schema
from app.ai.schemas import ChatMessage, ProbeResult


class OpenAIRefusalError(RuntimeError):
    """Model declined to answer; treated as an AI failure, never parsed."""


class OpenAIChatProvider:
    provider_id = "openai"

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_s: float = 120.0,
    ) -> None:
        self._api_key = api_key
        self.model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def probe(self) -> ProbeResult:
        if not self._api_key:
            return ProbeResult(
                ok=False,
                reachable=False,
                provider=self.provider_id,
                model=self.model,
                detail="OPENAI_API_KEY not configured",
            )
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self._base_url}/models", headers=self._headers())
                resp.raise_for_status()
            return ProbeResult(
                ok=True,
                reachable=True,
                provider=self.provider_id,
                model=self.model,
                detail="OpenAI reachable",
            )
        except Exception as exc:
            return ProbeResult(
                ok=False,
                reachable=False,
                provider=self.provider_id,
                model=self.model,
                detail=f"OpenAI unreachable: {exc}",
            )

    def complete_json(
        self,
        messages: list[ChatMessage],
        schema: dict[str, Any],
        *,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        """Bind the response to ``schema`` via Structured Outputs.

        ``json_object`` mode only guarantees parseable JSON, not the requested
        shape, which silently produced renamed/reshaped fields that call-site
        validators then rejected. Strict ``json_schema`` makes the shape a
        provider guarantee; models or gateways that reject it downgrade.
        """
        timeout = timeout_s if timeout_s is not None else self._timeout_s
        body = [m.model_dump() for m in messages]

        response_format = self._json_schema_format(schema)
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": body,
                    "response_format": response_format,
                },
            )
            if response_format["type"] == "json_schema" and self._schema_rejected(resp):
                resp = client.post(
                    f"{self._base_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": self.model,
                        "messages": body,
                        "response_format": {"type": "json_object"},
                    },
                )
            resp.raise_for_status()
            message = resp.json()["choices"][0]["message"]

        refusal = message.get("refusal")
        if refusal:
            raise OpenAIRefusalError(str(refusal)[:300])

        parsed = json.loads(message["content"])
        return parsed if isinstance(parsed, dict) else {"value": parsed}

    def _json_schema_format(self, schema: dict[str, Any]) -> dict[str, Any]:
        if not schema:
            return {"type": "json_object"}
        try:
            strict = to_strict_schema(schema)
        except UnsupportedSchemaError:
            return {"type": "json_object"}
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "archavow_response",
                "schema": strict,
                "strict": True,
            },
        }

    @staticmethod
    def _schema_rejected(resp: httpx.Response) -> bool:
        """True when the endpoint refused the schema itself, not the request content.

        Older snapshots and OpenAI-compatible gateways return 400 for an
        unsupported ``response_format``; retrying those in ``json_object`` mode
        keeps them working instead of failing the whole assist.
        """
        if resp.status_code != 400:
            return False
        try:
            detail = resp.json().get("error", {})
        except Exception:
            return True
        blob = " ".join(
            str(detail.get(k) or "") for k in ("message", "param", "code")
        ).lower()
        return "response_format" in blob or "json_schema" in blob or "schema" in blob

    def complete_text(
        self,
        messages: list[ChatMessage],
        *,
        timeout_s: float | None = None,
    ) -> str:
        timeout = timeout_s if timeout_s is not None else self._timeout_s
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": [m.model_dump() for m in messages],
                },
            )
            resp.raise_for_status()
            return str(resp.json()["choices"][0]["message"]["content"] or "")
