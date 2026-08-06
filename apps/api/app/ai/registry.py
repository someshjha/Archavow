"""Provider registry — add a provider without touching workflows."""

from __future__ import annotations

import os

from app.ai.protocols import ChatProvider, EmbeddingProvider
from app.ai.providers.null_embed import NullEmbeddingProvider
from app.ai.providers.ollama_chat import OllamaChatProvider
from app.ai.providers.ollama_embed import OllamaEmbeddingProvider
from app.ai.providers.openai_chat import OpenAIChatProvider
from app.ai.providers.openai_embed import OpenAIEmbeddingProvider
from app.ai.schemas import EffectiveAIConfig


def registered_chat_providers() -> frozenset[str]:
    return frozenset({"ollama", "openai"})


def registered_embedding_providers() -> frozenset[str]:
    return frozenset({"ollama", "openai", "none"})


def build_chat_provider(config: EffectiveAIConfig) -> ChatProvider:
    if config.chat_provider == "openai":
        return OpenAIChatProvider(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            model=config.chat_model,
            base_url=config.openai_base_url,
        )
    return OllamaChatProvider(
        base_url=config.ollama_base_url,
        model=config.chat_model,
    )


def build_embedding_provider(config: EffectiveAIConfig) -> EmbeddingProvider:
    if config.embedding_provider == "none":
        return NullEmbeddingProvider()
    if config.embedding_provider == "openai":
        return OpenAIEmbeddingProvider(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            model=config.embedding_model,
            dimensions=config.embedding_dimensions,
            base_url=config.openai_base_url,
        )
    return OllamaEmbeddingProvider(
        base_url=config.ollama_base_url,
        model=config.embedding_model,
        dimensions=config.embedding_dimensions,
    )
