"""OpenAI embedding provider."""

from __future__ import annotations

import httpx

from app.ai.schemas import ProbeResult


class OpenAIEmbeddingProvider:
    provider_id = "openai"

    def __init__(
        self,
        api_key: str,
        model: str,
        dimensions: int = 768,
        base_url: str = "https://api.openai.com/v1",
        timeout_s: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self.model = model
        self.dimensions = dimensions
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
                dimensions=self.dimensions,
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
                dimensions=self.dimensions,
                detail="OpenAI reachable",
            )
        except Exception as exc:
            return ProbeResult(
                ok=False,
                reachable=False,
                provider=self.provider_id,
                model=self.model,
                dimensions=self.dimensions,
                detail=f"OpenAI unreachable: {exc}",
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        with httpx.Client(timeout=self._timeout_s) as client:
            resp = client.post(
                f"{self._base_url}/embeddings",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "input": texts,
                    "dimensions": self.dimensions,
                },
            )
            resp.raise_for_status()
            data = resp.json().get("data") or []
        # OpenAI returns objects with index
        ordered = sorted(data, key=lambda d: int(d.get("index", 0)))
        return [[float(x) for x in row.get("embedding") or []] for row in ordered]
