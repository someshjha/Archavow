"""RED until resolve_effective_ai_config is implemented."""

from __future__ import annotations

import os

import pytest

from app.ai.config import resolve_effective_ai_config


def test_defaults_from_env(env_ollama_defaults: None) -> None:
    cfg = resolve_effective_ai_config(env=os.environ)
    assert cfg.chat_provider == "ollama"
    assert cfg.chat_model == "llama3.2"
    assert cfg.embedding_provider == "none"
    assert cfg.embedding_dimensions == 768
    assert cfg.ollama_base_url == "http://127.0.0.1:11434"
    assert cfg.openai_api_key_configured is False


def test_openai_chat_from_env(monkeypatch: pytest.MonkeyPatch, env_ollama_defaults: None) -> None:
    monkeypatch.setenv("AI_CHAT_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    cfg = resolve_effective_ai_config(env=os.environ)
    assert cfg.chat_provider == "openai"
    assert cfg.chat_model == "gpt-4o-mini"
    assert cfg.openai_api_key_configured is True


def test_workspace_overrides_beat_env(env_ollama_defaults: None) -> None:
    cfg = resolve_effective_ai_config(
        env=os.environ,
        overrides={
            "chat_provider": "openai",
            "chat_model": "gpt-4o",
            "embedding_provider": "ollama",
            "embedding_model": "nomic-embed-text",
        },
    )
    assert cfg.chat_provider == "openai"
    assert cfg.chat_model == "gpt-4o"
    assert cfg.embedding_provider == "ollama"
    assert cfg.embedding_model == "nomic-embed-text"


def test_overrides_cannot_inject_api_key(monkeypatch: pytest.MonkeyPatch, env_ollama_defaults: None) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = resolve_effective_ai_config(
        env=os.environ,
        overrides={"openai_api_key": "sk-leaked", "openai_api_key_configured": True},
    )
    assert cfg.openai_api_key_configured is False


def test_mixed_providers_allowed(env_ollama_defaults: None) -> None:
    cfg = resolve_effective_ai_config(
        env=os.environ,
        overrides={"chat_provider": "openai", "embedding_provider": "ollama"},
    )
    assert cfg.chat_provider == "openai"
    assert cfg.embedding_provider == "ollama"


def test_embedding_none_is_valid(env_ollama_defaults: None) -> None:
    cfg = resolve_effective_ai_config(
        env=os.environ,
        overrides={"embedding_provider": "none"},
    )
    assert cfg.embedding_provider == "none"


def test_hld_fallback_chain_defaults_to_current_provider_plus_ollama(
    env_ollama_defaults: None,
) -> None:
    cfg = resolve_effective_ai_config(
        env=os.environ, overrides={"chat_provider": "openai", "chat_model": "gpt-4o-mini"}
    )
    assert [(m.provider, m.model) for m in cfg.hld_fallback_chain] == [
        ("openai", "gpt-4o-mini"),
        ("ollama", "llama3.2"),
    ]


def test_hld_fallback_chain_dedupes_when_already_ollama(env_ollama_defaults: None) -> None:
    cfg = resolve_effective_ai_config(env=os.environ)
    assert cfg.chat_provider == "ollama"
    assert cfg.chat_model == "llama3.2"
    assert [(m.provider, m.model) for m in cfg.hld_fallback_chain] == [("ollama", "llama3.2")]


def test_hld_fallback_chain_override_is_respected(env_ollama_defaults: None) -> None:
    cfg = resolve_effective_ai_config(
        env=os.environ,
        overrides={
            "hld_fallback_chain": [
                {"provider": "openai", "model": "gpt-4o"},
                {"provider": "ollama", "model": "mistral"},
            ]
        },
    )
    assert [(m.provider, m.model) for m in cfg.hld_fallback_chain] == [
        ("openai", "gpt-4o"),
        ("ollama", "mistral"),
    ]


def test_hld_fallback_chain_normalizes_oai_provider_alias(
    monkeypatch: pytest.MonkeyPatch, env_ollama_defaults: None
) -> None:
    """Regression: AI_CHAT_PROVIDER="oai" (a first-class alias elsewhere in this
    module) used to crash resolve_effective_ai_config because the raw,
    unnormalized chat_provider string was fed straight into ChatModelRef's
    strict Literal["ollama", "openai"] field, which has no normalizing
    validator (unlike EffectiveAIConfig.chat_provider)."""
    monkeypatch.setenv("AI_CHAT_PROVIDER", "oai")
    cfg = resolve_effective_ai_config(env=os.environ)
    assert cfg.chat_provider == "openai"
    assert cfg.hld_fallback_chain[0].provider == "openai"
    assert cfg.hld_fallback_chain[0].model == "gpt-4o-mini"
