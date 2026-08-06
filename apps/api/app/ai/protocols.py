"""AI provider ports. Implementations live under app.ai.providers."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.ai.schemas import ChatMessage, ProbeResult


@runtime_checkable
class ChatProvider(Protocol):
    provider_id: str
    model: str

    def probe(self) -> ProbeResult: ...

    def complete_json(
        self,
        messages: list[ChatMessage],
        schema: dict[str, Any],
        *,
        timeout_s: float | None = None,
    ) -> dict[str, Any]: ...

    def complete_text(
        self,
        messages: list[ChatMessage],
        *,
        timeout_s: float | None = None,
    ) -> str: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    provider_id: str
    model: str
    dimensions: int

    def probe(self) -> ProbeResult: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...
