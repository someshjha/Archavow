"""Test doubles for AI ports — no network."""

from __future__ import annotations

from typing import Any

from app.ai.schemas import ChatMessage, ProbeResult


class FakeChatProvider:
    provider_id = "fake-chat"
    model = "fake-model"

    def __init__(
        self,
        *,
        json_response: dict[str, Any] | None = None,
        text_response: str = "ok",
        probe_ok: bool = True,
        empty_json: bool = False,
    ) -> None:
        self.json_response = json_response if json_response is not None else {"title": "x"}
        self.text_response = text_response
        self.probe_ok = probe_ok
        self.empty_json = empty_json
        self.complete_json_calls = 0
        self.complete_text_calls = 0

    def probe(self) -> ProbeResult:
        return ProbeResult(
            ok=self.probe_ok,
            reachable=self.probe_ok,
            provider=self.provider_id,
            model=self.model,
            detail=None if self.probe_ok else "unreachable",
        )

    def complete_json(
        self,
        messages: list[ChatMessage],
        schema: dict[str, Any],
        *,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        self.complete_json_calls += 1
        if self.empty_json:
            return {}
        return dict(self.json_response)

    def complete_text(
        self,
        messages: list[ChatMessage],
        *,
        timeout_s: float | None = None,
    ) -> str:
        self.complete_text_calls += 1
        return self.text_response


class FakeEmbeddingProvider:
    provider_id = "fake-embed"
    model = "fake-embed-model"
    dimensions = 768

    def __init__(
        self,
        *,
        probe_ok: bool = True,
        wrong_dim: bool = False,
    ) -> None:
        self.probe_ok = probe_ok
        self.wrong_dim = wrong_dim
        self.embed_calls: list[list[str]] = []

    def probe(self) -> ProbeResult:
        return ProbeResult(
            ok=self.probe_ok,
            reachable=self.probe_ok,
            provider=self.provider_id,
            model=self.model,
            dimensions=self.dimensions,
            detail=None if self.probe_ok else "unreachable",
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls.append(list(texts))
        dim = 16 if self.wrong_dim else self.dimensions
        return [[0.01 * (i + 1)] * dim for i, _ in enumerate(texts)]
