"""Shared AI DTOs — contract for gateway + settings."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ChatProviderId = Literal["ollama", "openai"]
EmbeddingProviderId = Literal["ollama", "openai", "none"]


class ChatModelRef(BaseModel):
    provider: ChatProviderId
    model: str = Field(min_length=1, max_length=128)


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ProbeResult(BaseModel):
    ok: bool
    reachable: bool
    provider: str
    model: str | None = None
    detail: str | None = None
    dimensions: int | None = None


class EffectiveAIConfig(BaseModel):
    """Resolved chat + embedding config (env ⊕ workspace settings)."""

    chat_provider: ChatProviderId = "ollama"
    chat_model: str = "llama3.2"
    embedding_provider: EmbeddingProviderId = "none"
    embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = Field(default=768, ge=768, le=768)
    ollama_base_url: str = "http://127.0.0.1:11434"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key_configured: bool = False
    hld_fallback_chain: list[ChatModelRef] = Field(default_factory=list, max_length=4)

    @field_validator("chat_provider", mode="before")
    @classmethod
    def _norm_chat(cls, v: Any) -> str:
        raw = str(v or "ollama").strip().lower()
        if raw in {"openai", "oai"}:
            return "openai"
        return "ollama"

    @field_validator("embedding_provider", mode="before")
    @classmethod
    def _norm_embed(cls, v: Any) -> str:
        raw = str(v or "none").strip().lower()
        if raw in {"openai", "oai"}:
            return "openai"
        if raw in {"ollama"}:
            return "ollama"
        return "none"


class AISettingsUpdate(BaseModel):
    chat_provider: ChatProviderId | None = None
    chat_model: str | None = Field(default=None, max_length=128)
    embedding_provider: EmbeddingProviderId | None = None
    embedding_model: str | None = Field(default=None, max_length=128)
    embedding_dimensions: int | None = Field(default=None, ge=768, le=768)
    ollama_base_url: str | None = None
    openai_base_url: str | None = None
    hld_fallback_chain: list[ChatModelRef] | None = Field(default=None, max_length=4)


class GenerationProvenance(BaseModel):
    """Required on every AI generation persist."""

    chat_provider: str
    chat_model: str
    embedding_provider: str
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
    workflow_version: str
    source_chunk_ids: list[str] = Field(default_factory=list)
