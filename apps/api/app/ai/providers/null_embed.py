"""Null embedding provider — semantic search off."""

from __future__ import annotations

from app.ai.gateway import EmbeddingDisabledError
from app.ai.schemas import ProbeResult


class NullEmbeddingProvider:
    provider_id = "none"
    model = ""
    dimensions = 0

    def probe(self) -> ProbeResult:
        return ProbeResult(
            ok=True,
            reachable=True,
            provider="none",
            model="",
            dimensions=0,
            detail="embeddings disabled",
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingDisabledError("embeddings are disabled (embedding_provider=none)")
