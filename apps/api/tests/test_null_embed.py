"""RED until NullEmbeddingProvider behavior is filled in."""

from __future__ import annotations

import pytest

from app.ai.providers.null_embed import NullEmbeddingProvider
from app.ai.gateway import EmbeddingDisabledError


def test_null_probe_ok_without_network() -> None:
    emb = NullEmbeddingProvider()
    result = emb.probe()
    assert result.ok is True
    assert result.reachable is True
    assert result.provider == "none"
    assert result.dimensions == 0 or result.dimensions is None


def test_null_embed_raises() -> None:
    emb = NullEmbeddingProvider()
    with pytest.raises((EmbeddingDisabledError, RuntimeError, NotImplementedError)):
        emb.embed(["hello"])
