"""RED until registry builds real / null providers from config."""

from __future__ import annotations

import pytest

from app.ai.registry import (
    build_chat_provider,
    build_embedding_provider,
    registered_chat_providers,
    registered_embedding_providers,
)
from app.ai.schemas import EffectiveAIConfig


def test_registered_provider_ids() -> None:
    assert registered_chat_providers() == frozenset({"ollama", "openai"})
    assert registered_embedding_providers() == frozenset({"ollama", "openai", "none"})


def test_build_null_embedding() -> None:
    cfg = EffectiveAIConfig(embedding_provider="none")
    emb = build_embedding_provider(cfg)
    assert emb.provider_id == "none"
    probe = emb.probe()
    assert probe.ok is True
    assert probe.provider == "none"
    # embed must fail closed
    with pytest.raises(Exception):
        emb.embed(["x"])


def test_build_ollama_chat_has_ids() -> None:
    cfg = EffectiveAIConfig(
        chat_provider="ollama",
        chat_model="llama3.2",
        ollama_base_url="http://127.0.0.1:9",
    )
    chat = build_chat_provider(cfg)
    assert chat.provider_id == "ollama"
    assert chat.model == "llama3.2"


def test_build_openai_chat_has_ids() -> None:
    cfg = EffectiveAIConfig(
        chat_provider="openai",
        chat_model="gpt-4o-mini",
        openai_base_url="https://api.openai.com/v1",
    )
    chat = build_chat_provider(cfg)
    assert chat.provider_id == "openai"
    assert chat.model == "gpt-4o-mini"


def test_build_ollama_embedding_dimensions() -> None:
    cfg = EffectiveAIConfig(
        embedding_provider="ollama",
        embedding_model="nomic-embed-text",
        embedding_dimensions=768,
        ollama_base_url="http://127.0.0.1:9",
    )
    emb = build_embedding_provider(cfg)
    assert emb.provider_id == "ollama"
    assert emb.dimensions == 768
