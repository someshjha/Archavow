"""Ollama embedding provider."""

from __future__ import annotations

import httpx

from app.ai.schemas import ProbeResult


class OllamaEmbeddingProvider:
    provider_id = "ollama"

    def __init__(
        self,
        base_url: str,
        model: str,
        dimensions: int = 768,
        timeout_s: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self.model = model
        self.dimensions = dimensions
        self._timeout_s = timeout_s

    def probe(self) -> ProbeResult:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self._base_url}/api/tags")
                resp.raise_for_status()
            return ProbeResult(
                ok=True,
                reachable=True,
                provider=self.provider_id,
                model=self.model,
                dimensions=self.dimensions,
                detail="Ollama reachable",
            )
        except Exception as exc:
            return ProbeResult(
                ok=False,
                reachable=False,
                provider=self.provider_id,
                model=self.model,
                dimensions=self.dimensions,
                detail=f"Ollama unreachable: {exc}",
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        with httpx.Client(timeout=self._timeout_s) as client:
            for text in texts:
                resp = client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                resp.raise_for_status()
                emb = resp.json().get("embedding") or []
                vectors.append([float(x) for x in emb])
        return vectors
