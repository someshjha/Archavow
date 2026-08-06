"""Unit tests for text chunking."""

from __future__ import annotations

from app.modules.knowledge.chunking import chunk_text


def test_chunk_text_splits_on_paragraphs() -> None:
    text = "Para one.\n\nPara two is longer and keeps going.\n\nPara three."
    chunks = chunk_text(text, max_chars=40)
    assert len(chunks) >= 2
    assert all(c.text.strip() for c in chunks)
    assert all(c.index >= 0 for c in chunks)


def test_chunk_text_empty() -> None:
    assert chunk_text("   ") == []


def test_heading_is_first_line_and_truncated() -> None:
    long_body = "word " * 100
    text = f"## Executive summary\n{long_body}\n\n## Next\nShort."
    chunks = chunk_text(text, max_chars=200)
    assert chunks
    for c in chunks:
        if c.heading:
            assert "\n" not in c.heading
            assert len(c.heading) <= 256
    assert any(c.heading == "Executive summary" for c in chunks)
