"""Ollama chat provider."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.ai.schemas import ChatMessage, ProbeResult


class OllamaChatProvider:
    provider_id = "ollama"

    def __init__(self, base_url: str, model: str, timeout_s: float = 120.0) -> None:
        self._base_url = base_url.rstrip("/")
        self.model = model
        self._timeout_s = timeout_s

    def probe(self) -> ProbeResult:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self._base_url}/api/tags")
                resp.raise_for_status()
                payload = resp.json()
            names = [
                str(item.get("name") or "")
                for item in (payload.get("models") or [])
                if isinstance(item, dict)
            ]
            present = any(
                n == self.model or n.startswith(f"{self.model}:") for n in names
            )
            return ProbeResult(
                ok=present,
                reachable=True,
                provider=self.provider_id,
                model=self.model,
                detail=(
                    f"Ollama reachable; '{self.model}' "
                    + ("present" if present else "not pulled")
                ),
            )
        except Exception as exc:
            return ProbeResult(
                ok=False,
                reachable=False,
                provider=self.provider_id,
                model=self.model,
                detail=f"Ollama unreachable: {exc}",
            )

    def complete_json(
        self,
        messages: list[ChatMessage],
        schema: dict[str, Any],
        *,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)
        if schema:
            prompt += f"\nRespond with JSON matching schema: {json.dumps(schema)}"
        timeout = timeout_s if timeout_s is not None else self._timeout_s
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            resp.raise_for_status()
            raw = resp.json().get("response") or "{}"
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        return parsed if isinstance(parsed, dict) else {"value": parsed}

    def complete_text(
        self,
        messages: list[ChatMessage],
        *,
        timeout_s: float | None = None,
    ) -> str:
        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)
        timeout = timeout_s if timeout_s is not None else self._timeout_s
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{self._base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            return str(resp.json().get("response") or "")
