"""RED until AIGateway methods are implemented (use fakes — no network)."""

from __future__ import annotations

import pytest

from app.ai.gateway import (
    AIGateway,
    EmbeddingDisabledError,
    EmptyAIResponseError,
)
from app.ai.schemas import ChatMessage, EffectiveAIConfig
from tests.fakes import FakeChatProvider, FakeEmbeddingProvider


def _gateway(
    *,
    empty_json: bool = False,
    embed_none: bool = False,
    wrong_dim: bool = False,
) -> AIGateway:
    cfg = EffectiveAIConfig(
        chat_provider="ollama",
        chat_model="llama3.2",
        embedding_provider="none" if embed_none else "ollama",
        embedding_model="nomic-embed-text",
        embedding_dimensions=768,
    )
    chat = FakeChatProvider(empty_json=empty_json)
    if embed_none:
        from app.ai.providers.null_embed import NullEmbeddingProvider

        emb: FakeEmbeddingProvider | NullEmbeddingProvider = NullEmbeddingProvider()
    else:
        emb = FakeEmbeddingProvider(wrong_dim=wrong_dim)
    return AIGateway(cfg, chat, emb)  # type: ignore[arg-type]


def test_complete_json_delegates_and_returns() -> None:
    gw = _gateway()
    out = gw.complete_json(
        [ChatMessage(role="user", content="hi")],
        schema={"type": "object"},
    )
    assert out == {"title": "x"}
    assert isinstance(gw.chat, FakeChatProvider)
    assert gw.chat.complete_json_calls == 1


def test_complete_json_rejects_empty() -> None:
    gw = _gateway(empty_json=True)
    with pytest.raises(EmptyAIResponseError):
        gw.complete_json([ChatMessage(role="user", content="hi")], schema={})


def test_complete_text_delegates() -> None:
    gw = _gateway()
    assert gw.complete_text([ChatMessage(role="user", content="hi")]) == "ok"


def test_embed_validates_dimensions() -> None:
    gw = _gateway()
    vectors = gw.embed(["a", "b"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 768


def test_embed_rejects_wrong_dimensions() -> None:
    gw = _gateway(wrong_dim=True)
    with pytest.raises(ValueError, match="dimension"):
        gw.embed(["a"])


def test_embed_disabled_when_none() -> None:
    gw = _gateway(embed_none=True)
    with pytest.raises(EmbeddingDisabledError):
        gw.embed(["a"])


def test_probe_all_keys() -> None:
    gw = _gateway()
    result = gw.probe_all()
    assert set(result) >= {"chat", "embeddings"}
    assert result["chat"].ok is True
    assert result["embeddings"].ok is True


def test_provenance_snapshot() -> None:
    gw = _gateway()
    prov = gw.provenance(workflow_version="gen.v1", source_chunk_ids=["c1"])
    assert prov.chat_provider == "ollama"
    assert prov.chat_model == "llama3.2"
    assert prov.embedding_provider == "ollama"
    assert prov.workflow_version == "gen.v1"
    assert prov.source_chunk_ids == ["c1"]


def test_provenance_when_embeddings_none() -> None:
    gw = _gateway(embed_none=True)
    prov = gw.provenance(workflow_version="gen.v1")
    assert prov.embedding_provider == "none"
    assert prov.embedding_model is None or prov.embedding_model == ""
