"""AIGateway — sole entry point for modules (copilot, knowledge, interview)."""

from __future__ import annotations

from typing import Any

from app.ai.protocols import ChatProvider, EmbeddingProvider
from app.ai.schemas import (
    ChatMessage,
    EffectiveAIConfig,
    GenerationProvenance,
    ProbeResult,
)


class EmptyAIResponseError(ValueError):
    """Raised when a provider returns empty / invalid structured output."""


class EmbeddingDisabledError(RuntimeError):
    """Raised when embed() is called while embedding_provider is none."""


class AIGateway:
    def __init__(
        self,
        config: EffectiveAIConfig,
        chat: ChatProvider,
        embeddings: EmbeddingProvider,
    ) -> None:
        self.config = config
        self.chat = chat
        self.embeddings = embeddings

    def probe_chat(self) -> ProbeResult:
        return self.chat.probe()

    def probe_embeddings(self) -> ProbeResult:
        return self.embeddings.probe()

    def probe_all(self) -> dict[str, ProbeResult]:
        return {
            "chat": self.probe_chat(),
            "embeddings": self.probe_embeddings(),
        }

    def complete_json(
        self,
        messages: list[ChatMessage],
        schema: dict[str, Any],
        *,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        from app.ai.json_schema import validate_against_schema

        result = self.chat.complete_json(messages, schema, timeout_s=timeout_s)
        if not result:
            raise EmptyAIResponseError("chat provider returned empty JSON")
        # Wire format may strip min/max/pattern; enforce the original contract here
        # and return the normalized object (optional nulls dropped as omit).
        if schema:
            return validate_against_schema(result, schema)
        return result

    def complete_text(
        self,
        messages: list[ChatMessage],
        *,
        timeout_s: float | None = None,
    ) -> str:
        return self.chat.complete_text(messages, timeout_s=timeout_s)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.config.embedding_provider == "none" or self.embeddings.provider_id == "none":
            raise EmbeddingDisabledError("embeddings are disabled (embedding_provider=none)")
        vectors = self.embeddings.embed(texts)
        expected = self.config.embedding_dimensions
        for i, vec in enumerate(vectors):
            if len(vec) != expected:
                raise ValueError(
                    f"embedding dimension mismatch at index {i}: "
                    f"got {len(vec)}, expected {expected}"
                )
        return vectors

    def provenance(
        self,
        *,
        workflow_version: str,
        source_chunk_ids: list[str] | None = None,
    ) -> GenerationProvenance:
        emb_none = self.config.embedding_provider == "none"
        return GenerationProvenance(
            chat_provider=self.config.chat_provider,
            chat_model=self.config.chat_model,
            embedding_provider=self.config.embedding_provider,
            embedding_model=None if emb_none else self.config.embedding_model,
            embedding_dimensions=None if emb_none else self.config.embedding_dimensions,
            workflow_version=workflow_version,
            source_chunk_ids=list(source_chunk_ids or []),
        )


def build_gateway(config: EffectiveAIConfig) -> AIGateway:
    from app.ai.registry import build_chat_provider, build_embedding_provider

    return AIGateway(
        config,
        build_chat_provider(config),
        build_embedding_provider(config),
    )
