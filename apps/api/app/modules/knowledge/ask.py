"""Ask-the-knowledge-base flow: score KB candidates, fall back to web/model."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.ai.config import resolve_effective_ai_config
from app.ai.gateway import build_gateway
from app.db.models import KnowledgeChunkRow, KnowledgeDocumentRow
from app.modules.knowledge.ingest import ingest_document
from app.modules.knowledge.retrieval import _tokenize, search
from app.modules.knowledge.schemas import (
    AskRequest,
    AskResult,
    DocumentCreate,
    DocumentOut,
    SearchHit,
    SearchRequest,
)
from app.modules.settings import service as settings_service

_KB_SCORE_FLOOR = 0.45
_KB_CONFIDENCE_FLOOR = 0.45


def _extract_points(query: str, hits: list[SearchHit], *, max_points: int = 5) -> list[str]:
    """Deterministic precise bullets from matched sentences."""
    q_tokens = _tokenize(query)
    points: list[str] = []
    seen: set[str] = set()
    for hit in hits:
        text = re.sub(r"\s+", " ", hit.text).strip()
        sentences = re.split(r"(?<=[.!?])\s+", text)
        ranked: list[tuple[int, str]] = []
        for sent in sentences:
            s = sent.strip(" -\t•*")
            if len(s) < 24 or len(s) > 280:
                continue
            if s.startswith("<!--") or s.startswith("http"):
                continue
            overlap = len(q_tokens & _tokenize(s))
            if overlap <= 0 and hit.score < 0.35:
                continue
            ranked.append((overlap, s))
        ranked.sort(key=lambda t: (-t[0], len(t[1])))
        for _, s in ranked[:2]:
            key = s.lower()[:80]
            if key in seen:
                continue
            seen.add(key)
            points.append(s)
            if len(points) >= max_points:
                return points
    if not points and hits:
        first = re.split(r"[\n.]", hits[0].text)[0].strip()
        if first:
            points.append(first[:240])
    return points


def _public_citations(hits: list[SearchHit], *, limit: int = 5) -> list[SearchHit]:
    out: list[SearchHit] = []
    for h in hits[:limit]:
        klass = "industry" if h.source_class == "seed" else h.source_class
        out.append(
            SearchHit(
                document_id=h.document_id,
                chunk_id=h.chunk_id,
                title=h.title,
                source_class=klass,
                text=h.text[:420],
                score=h.score,
                citation=h.citation,
            )
        )
    return out


def ask(db: Session, payload: AskRequest) -> AskResult:
    """Score KB candidates; fall back to web/model when knowledge is weak."""
    from app.ai.knowledge_assist import answer_online_or_model, compose_scored_knowledge_answer

    search_result = search(
        db, SearchRequest(query=payload.query, limit=payload.limit)
    )
    hits = search_result.hits
    cfg = resolve_effective_ai_config(overrides=settings_service.get_overrides(db))
    gateway = build_gateway(cfg)

    composed = None
    if hits:
        composed = compose_scored_knowledge_answer(gateway, payload.query, hits)

    use_fallback = (
        not hits
        or composed is None
        or not composed.answer
        or composed.best_candidate_score < _KB_SCORE_FLOOR
        or composed.confidence < _KB_CONFIDENCE_FLOOR
        or composed.status.status != "ok"
    )

    if use_fallback:
        online = answer_online_or_model(gateway, payload.query)
        if online.answer:
            # Model/web answers must not inherit rejected KB hits as provenance
            return AskResult(
                answer=online.answer,
                points=online.points,
                pattern_name=online.pattern_name,
                mermaid=online.mermaid,
                confidence=online.confidence,
                source=online.source,
                grounded=False,
                citations=[],
                retrieval_status=search_result.retrieval_status,
                ai_assist={
                    **online.status.model_dump(),
                    "fallback": True,
                    "kb_best": (composed.best_candidate_score if composed else 0),
                },
            )
        if hits:
            points = _extract_points(payload.query, hits)
            answer = (
                "\n".join(f"- {p}" for p in points)
                if points
                else hits[0].text.strip()[:400]
            )
            citations = _public_citations(hits)
            return AskResult(
                answer=answer,
                points=points,
                citations=citations,
                retrieval_status=search_result.retrieval_status,
                source="knowledge",
                grounded=bool(citations),
                confidence=0.35,
                ai_assist={"status": "skipped", "detail": "deterministic_fallback"},
            )
        return AskResult(
            answer="I could not find a reliable architecture answer for that question yet.",
            points=[],
            citations=[],
            retrieval_status=search_result.retrieval_status,
            source="model",
            grounded=False,
            ai_assist={"status": "failed", "detail": "no_answer"},
        )

    assert composed is not None
    citations = _public_citations(hits)
    return AskResult(
        answer=composed.answer,
        points=composed.points or _extract_points(payload.query, hits),
        pattern_name=composed.pattern_name,
        mermaid=composed.mermaid,
        confidence=composed.confidence,
        source="knowledge",
        grounded=bool(citations),
        citations=citations,
        retrieval_status=search_result.retrieval_status,
        ai_assist=composed.status.model_dump(),
    )


def capture_project_decision(
    db: Session,
    *,
    project_name: str,
    project_id: str,
    option_title: str,
    option_summary: str,
    adrs: list[dict],
    risks: list[dict],
    backlog: list[dict],
    quality_score: dict | None,
    hld_excerpt: str,
) -> DocumentOut | None:
    """Persist architecture choices into the searchable knowledge library."""
    lines = [
        f"# Architecture decisions — {project_name}",
        "",
        f"Project id: `{project_id}`",
        "",
        "## Selected option",
        "",
        f"**{option_title}**",
        "",
        option_summary or "",
        "",
    ]
    if quality_score:
        lines.extend(
            [
                "## Evidence checklist",
                "",
                f"Overall coverage: {quality_score.get('overall', '—')}",
                "",
            ]
        )
    if adrs:
        lines.extend(["## ADRs", ""])
        for adr in adrs:
            lines.extend(
                [
                    f"### {adr.get('id', 'ADR')}: {adr.get('title', '')}",
                    "",
                    f"Status: {adr.get('status', 'proposed')}",
                    "",
                    str(adr.get("decision") or ""),
                    "",
                ]
            )
    if risks:
        lines.extend(["## Risks", ""])
        for r in risks[:8]:
            lines.append(
                f"- {r.get('id')}: {r.get('title')} ({r.get('severity')}) — {r.get('mitigation', '')}"
            )
        lines.append("")
    if backlog:
        lines.extend(["## Backlog", ""])
        for b in backlog[:8]:
            lines.append(f"- {b.get('priority')}: {b.get('title')}")
        lines.append("")
    if hld_excerpt:
        lines.extend(["## HLD excerpt", "", hld_excerpt[:2500], ""])

    content = "\n".join(lines)
    title = f"Project decisions — {project_name}"[:256]
    existing = (
        db.query(KnowledgeDocumentRow)
        .filter(
            KnowledgeDocumentRow.source_class == "project",
            KnowledgeDocumentRow.title == title,
        )
        .first()
    )
    if existing is not None:
        db.query(KnowledgeChunkRow).filter(
            KnowledgeChunkRow.document_id == existing.id
        ).delete()
        db.delete(existing)
        db.commit()

    return ingest_document(
        db,
        DocumentCreate(title=title, content=content, source_class="project"),
    )
