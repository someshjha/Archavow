"""Schema contracts — should stay green (define the AI DTO surface)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.ai.schemas import AISettingsUpdate, EffectiveAIConfig, GenerationProvenance


def test_effective_config_defaults() -> None:
    cfg = EffectiveAIConfig()
    assert cfg.chat_provider == "ollama"
    assert cfg.embedding_provider == "none"
    assert cfg.embedding_dimensions == 768
    assert cfg.openai_api_key_configured is False


def test_normalizes_provider_aliases() -> None:
    cfg = EffectiveAIConfig(chat_provider="OAI", embedding_provider="OpenAI")
    assert cfg.chat_provider == "openai"
    assert cfg.embedding_provider == "openai"


def test_rejects_unknown_embedding_as_none() -> None:
    cfg = EffectiveAIConfig(embedding_provider="azure-something")
    assert cfg.embedding_provider == "none"


def test_settings_update_partial() -> None:
    upd = AISettingsUpdate(embedding_provider="ollama", embedding_model="nomic-embed-text")
    assert upd.chat_provider is None
    assert upd.embedding_provider == "ollama"


def test_provenance_requires_workflow_version() -> None:
    with pytest.raises(ValidationError):
        GenerationProvenance(  # type: ignore[call-arg]
            chat_provider="ollama",
            chat_model="llama3.2",
            embedding_provider="none",
        )
