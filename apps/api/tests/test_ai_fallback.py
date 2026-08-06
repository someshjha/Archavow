"""Model fallback chain — first entry fails, next one is tried."""

from __future__ import annotations

from app.ai.fallback import complete_json_with_fallback
from app.ai.gateway import AIGateway
from app.ai.schemas import ChatMessage, ChatModelRef, EffectiveAIConfig
from tests.fakes import FakeChatProvider, FakeEmbeddingProvider

_SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
_MESSAGES = [ChatMessage(role="user", content="hi")]


def _base_config() -> EffectiveAIConfig:
    return EffectiveAIConfig(chat_provider="openai", chat_model="gpt-4o-mini")


def test_falls_back_to_second_entry_when_first_fails() -> None:
    chain = [
        ChatModelRef(provider="openai", model="gpt-4o-mini"),
        ChatModelRef(provider="ollama", model="llama3.2"),
    ]

    def factory(cfg: EffectiveAIConfig) -> AIGateway:
        if cfg.chat_provider == "openai":
            chat = FakeChatProvider()
            chat.complete_json = lambda *a, **k: (_ for _ in ()).throw(ConnectionError("down"))  # type: ignore[method-assign]
        else:
            chat = FakeChatProvider(json_response={"ok": True})
        return AIGateway(cfg, chat, FakeEmbeddingProvider())

    result, entry, status = complete_json_with_fallback(
        chain, _MESSAGES, _SCHEMA, base_config=_base_config(), gateway_factory=factory
    )
    assert result == {"ok": True}
    assert entry is not None
    assert (entry.provider, entry.model) == ("ollama", "llama3.2")
    assert status.status == "ok"


def test_returns_failed_status_when_every_entry_fails() -> None:
    chain = [
        ChatModelRef(provider="openai", model="gpt-4o-mini"),
        ChatModelRef(provider="ollama", model="llama3.2"),
    ]

    def factory(cfg: EffectiveAIConfig) -> AIGateway:
        chat = FakeChatProvider()
        chat.complete_json = lambda *a, **k: (_ for _ in ()).throw(ConnectionError("down"))  # type: ignore[method-assign]
        return AIGateway(cfg, chat, FakeEmbeddingProvider())

    result, entry, status = complete_json_with_fallback(
        chain, _MESSAGES, _SCHEMA, base_config=_base_config(), gateway_factory=factory
    )
    assert result is None
    assert entry is None
    assert status.status == "failed"


def test_is_valid_rejects_result_and_falls_through_to_next_entry() -> None:
    chain = [
        ChatModelRef(provider="openai", model="gpt-4o-mini"),
        ChatModelRef(provider="ollama", model="llama3.2"),
    ]

    def factory(cfg: EffectiveAIConfig) -> AIGateway:
        if cfg.chat_provider == "openai":
            chat = FakeChatProvider(json_response={"ok": False})
        else:
            chat = FakeChatProvider(json_response={"ok": True})
        return AIGateway(cfg, chat, FakeEmbeddingProvider())

    result, entry, status = complete_json_with_fallback(
        chain,
        _MESSAGES,
        _SCHEMA,
        base_config=_base_config(),
        gateway_factory=factory,
        is_valid=lambda r: r.get("ok") is True,
    )
    assert result == {"ok": True}
    assert entry is not None
    assert (entry.provider, entry.model) == ("ollama", "llama3.2")
    assert status.status == "ok"


def test_is_valid_none_preserves_default_behavior() -> None:
    chain = [ChatModelRef(provider="ollama", model="llama3.2")]

    def factory(cfg: EffectiveAIConfig) -> AIGateway:
        chat = FakeChatProvider(json_response={"ok": False})
        return AIGateway(cfg, chat, FakeEmbeddingProvider())

    result, entry, status = complete_json_with_fallback(
        chain, _MESSAGES, _SCHEMA, base_config=_base_config(), gateway_factory=factory
    )
    assert result == {"ok": False}
    assert entry is not None
    assert status.status == "ok"


def test_empty_chain_fails_immediately_without_calling_factory() -> None:
    calls = {"n": 0}

    def factory(cfg: EffectiveAIConfig) -> AIGateway:
        calls["n"] += 1
        return AIGateway(cfg, FakeChatProvider(), FakeEmbeddingProvider())

    result, entry, status = complete_json_with_fallback(
        [], _MESSAGES, _SCHEMA, base_config=_base_config(), gateway_factory=factory
    )
    assert result is None
    assert entry is None
    assert status.status == "failed"
    assert calls["n"] == 0


def test_openai_entry_skipped_without_calling_factory_when_key_not_configured() -> None:
    """An openai chain entry is a guaranteed 401 when no API key is configured —
    skip it (record a per-entry failure status) rather than pay the round trip,
    and still fall through to the next entry."""
    calls: list[str] = []

    chain = [
        ChatModelRef(provider="openai", model="gpt-4o-mini"),
        ChatModelRef(provider="ollama", model="llama3.2"),
    ]

    def factory(cfg: EffectiveAIConfig) -> AIGateway:
        calls.append(cfg.chat_provider)
        return AIGateway(cfg, FakeChatProvider(json_response={"ok": True}), FakeEmbeddingProvider())

    base_config = EffectiveAIConfig(
        chat_provider="openai", chat_model="gpt-4o-mini", openai_api_key_configured=False
    )
    result, entry, status = complete_json_with_fallback(
        chain, _MESSAGES, _SCHEMA, base_config=base_config, gateway_factory=factory
    )
    assert calls == ["ollama"]  # factory never called for the unconfigured openai entry
    assert result == {"ok": True}
    assert entry is not None
    assert (entry.provider, entry.model) == ("ollama", "llama3.2")
    assert status.status == "ok"


def test_openai_only_chain_fails_without_calling_factory_when_key_not_configured() -> None:
    calls = {"n": 0}

    def factory(cfg: EffectiveAIConfig) -> AIGateway:
        calls["n"] += 1
        return AIGateway(cfg, FakeChatProvider(), FakeEmbeddingProvider())

    chain = [ChatModelRef(provider="openai", model="gpt-4o-mini")]
    base_config = EffectiveAIConfig(
        chat_provider="openai", chat_model="gpt-4o-mini", openai_api_key_configured=False
    )
    result, entry, status = complete_json_with_fallback(
        chain, _MESSAGES, _SCHEMA, base_config=base_config, gateway_factory=factory
    )
    assert result is None
    assert entry is None
    assert status.status == "failed"
    assert status.detail == "openai_key_not_configured"
    assert calls["n"] == 0
