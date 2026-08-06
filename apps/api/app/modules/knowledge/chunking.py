"""Simple markdown / plain-text chunker."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


@dataclass
class TextChunk:
    index: int
    text: str
    heading: str | None = None


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_text(text: str, *, max_chars: int = 800) -> list[TextChunk]:
    cleaned = text.replace("\r\n", "\n").strip()
    if not cleaned:
        return []

    # Split on blank lines; keep headings attached when possible
    parts = re.split(r"\n{2,}", cleaned)
    chunks: list[TextChunk] = []
    buf = ""
    heading: str | None = None
    index = 0

    def flush() -> None:
        nonlocal buf, index, heading
        piece = buf.strip()
        if piece:
            safe_heading = heading[:256] if heading else None
            chunks.append(TextChunk(index=index, text=piece, heading=safe_heading))
            index += 1
        buf = ""

    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("#"):
            flush()
            # First line only — never store body text in heading (VARCHAR(256))
            first = part.lstrip("#").split("\n", 1)[0].strip()
            heading = (first[:256] if first else heading)
        if len(buf) + len(part) + 2 <= max_chars:
            buf = f"{buf}\n\n{part}".strip() if buf else part
        else:
            flush()
            if len(part) <= max_chars:
                buf = part
            else:
                # hard-split long paragraphs
                for i in range(0, len(part), max_chars):
                    slice_ = part[i : i + max_chars].strip()
                    if slice_:
                        safe_heading = heading[:256] if heading else None
                        chunks.append(
                            TextChunk(index=index, text=slice_, heading=safe_heading)
                        )
                        index += 1
                buf = ""
    flush()
    return chunks
