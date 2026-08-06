"""Knowledge retrieval scoring helpers."""

from __future__ import annotations

from app.modules.knowledge.service import _keyword_score, _phrase_boost, _tokenize


def test_tokenize_drops_stopwords() -> None:
    tokens = _tokenize("What are the required controls for Kafka client security?")
    assert "what" not in tokens
    assert "are" not in tokens
    assert "required" not in tokens
    assert "for" not in tokens
    assert "kafka" in tokens
    assert "client" in tokens
    assert "security" in tokens


def test_phrase_boost_prefers_exact_fragments() -> None:
    query = "Kafka client security"
    relevant = "Organization standard: Kafka client security must use mTLS."
    unrelated = "What are the required controls for business strategy reviews?"
    assert _phrase_boost(query, relevant) > _phrase_boost(query, unrelated)
    assert _keyword_score(query, relevant) >= _keyword_score(query, unrelated)
