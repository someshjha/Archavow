"""Architecture package generation and retrieval."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.ai.assist import enrich_package_summary
from app.ai.config import resolve_effective_ai_config
from app.db.models import ArchitectureOptionRow, ArchitecturePackageRow
from app.modules.knowledge import service as knowledge_service
from app.modules.options.generator import OptionTemplate
from app.modules.options.options_ops import _context
from app.modules.options.package_builders import (
    build_adrs,
    build_backlog,
    build_c4_component_mermaid,
    build_c4_container_mermaid,
    build_c4_mermaid,
    build_dataflow_mermaid,
    build_epics,
    build_hld_markdown,
    build_hld_markdown_ai,
    build_package_documents,
    build_quality_score,
    build_risks,
    build_sequence_mermaid,
    build_threats,
)
from app.modules.options.schemas import AdrOut, CitationOut, PackageOut, RiskOut
from app.modules.projects.service import get_project_row
from app.modules.requirements import service as req_service
from app.modules.settings import service as settings_service

logger = logging.getLogger("archavow.options")


def generate_package(db: Session, project_id: str) -> tuple[PackageOut | None, str | None]:
    """Returns (package, error). error='not_selected' → 409."""
    parsed = _context(db, project_id)
    if parsed is None:
        return None, "not_found"
    ctx, project_uuid = parsed

    from app.db.models import ProjectRow

    # Indirect through the service module (not a direct import) so callers/tests
    # that monkeypatch `service.build_gateway` still take effect here.
    from app.modules.options import service as _service

    locked = (
        db.query(ProjectRow)
        .filter(ProjectRow.id == project_uuid)
        .with_for_update()
        .first()
    )
    if locked is None:
        return None, "not_found"

    selected = (
        db.query(ArchitectureOptionRow)
        .filter(
            ArchitectureOptionRow.project_id == project_uuid,
            ArchitectureOptionRow.selected.is_(True),
        )
        .with_for_update()
        .first()
    )
    if selected is None:
        return None, "not_selected"

    design = selected.design if isinstance(getattr(selected, "design", None), dict) else {}
    tmpl = OptionTemplate(
        key=selected.key,
        title=selected.title,
        summary=selected.summary,
        pros=list(selected.pros or []),
        cons=list(selected.cons or []),
        fit_score=selected.fit_score,
        cost_band=selected.cost_band,
        ops_band=selected.ops_band,
        recommended=selected.recommended,
        stack=list(selected.stack or []),
        origin=selected.origin if selected.origin in {"template", "ai"} else "template",
        approach=str(design.get("approach") or "").strip(),
        assumptions=[
            str(a).strip() for a in (design.get("assumptions") or []) if str(a).strip()
        ],
        constraints=[
            str(c).strip() for c in (design.get("constraints") or []) if str(c).strip()
        ],
        key_decisions=[
            str(d).strip() for d in (design.get("key_decisions") or []) if str(d).strip()
        ],
    )

    # Keep under SearchRequest.query max_length (4000); long interview answers
    # used to blow this up and 500 right after a successful human-gate select.
    _SEARCH_QUERY_MAX = 4_000
    query = " ".join(
        part
        for part in [
            ctx.name,
            ctx.preferred_cloud,
            ctx.tech_constraints,
            ctx.scale_availability,
            tmpl.title,
            tmpl.summary,
            " ".join(tmpl.stack),
            " ".join(ctx.requirements[:12]),
        ]
        if part
    )
    query = (query or ctx.name)[:_SEARCH_QUERY_MAX].rstrip()
    search = knowledge_service.search(
        db, knowledge_service.SearchRequest(query=query or ctx.name[:_SEARCH_QUERY_MAX], limit=5)
    )
    citation_dicts = [
        {
            "document_id": h.document_id,
            "chunk_id": h.chunk_id,
            "title": h.title,
            "source_class": h.source_class,
            "citation": h.citation,
            "excerpt": h.text[:280],
            "text": h.text,
            "score": h.score,
        }
        for h in search.hits
    ]

    cfg = resolve_effective_ai_config(overrides=settings_service.get_overrides(db))
    gateway = _service.build_gateway(cfg)
    ai_summary, ai_status = enrich_package_summary(
        gateway,
        ctx,
        tmpl,
        citation_titles=[c["citation"] for c in citation_dicts],
    )
    ai_assist = ai_status.model_dump()

    try:
        hld, hld_source, hld_model = build_hld_markdown_ai(
            ctx,
            tmpl,
            citations=citation_dicts,
            executive_summary=ai_summary,
            fallback_chain=cfg.hld_fallback_chain,
            base_config=cfg,
            gateway_factory=_service.build_gateway,
        )
    except Exception:
        logger.warning(
            "HLD AI generation failed unexpectedly; falling back to deterministic template",
            exc_info=True,
        )
        hld = build_hld_markdown(ctx, tmpl, citations=citation_dicts, executive_summary=ai_summary)
        hld_source, hld_model = "template", None

    # Knowledge corpus must never accumulate AI-recycled content (it grounds future
    # HLD generations) — always capture the deterministic template's output as the
    # excerpt, regardless of which path produced the served `hld`.
    if hld_source == "template":
        template_hld_for_excerpt = hld
    else:
        template_hld_for_excerpt = build_hld_markdown(
            ctx, tmpl, citations=citation_dicts, executive_summary=ai_summary
        )

    mermaid = build_c4_mermaid(ctx, tmpl)
    mermaid_container = build_c4_container_mermaid(ctx, tmpl)
    mermaid_sequence = build_sequence_mermaid(ctx, tmpl)
    # Deployment topology was dropped — empty boxes and nested region/VPC
    # diagrams weren't earning their keep. C4 + sequence + data-flow cover it.
    mermaid_deploy = ""
    mermaid_component = build_c4_component_mermaid(ctx, tmpl)
    mermaid_dataflow = build_dataflow_mermaid(ctx, tmpl)
    adrs = build_adrs(ctx, tmpl)
    risks = build_risks(ctx, tmpl)
    backlog = build_backlog(ctx, tmpl)
    epics = build_epics(ctx, tmpl)
    threats = build_threats(ctx, tmpl)
    completeness = req_service.completeness_payload(db, project_id)
    completeness_overall = completeness.overall if completeness else 0
    evidence_cites = [
        c
        for c in citation_dicts
        if str(c.get("source_class") or "") in {"org", "project"}
    ]
    quality_score = build_quality_score(
        ctx,
        tmpl,
        completeness_overall=completeness_overall,
        evidence_citation_count=len(evidence_cites),
        org_standards_cited=any(c.get("source_class") == "org" for c in evidence_cites),
        completeness_categories=(
            {c.key: c.score for c in completeness.categories} if completeness else None
        ),
    )

    # All options for comparison artifact
    option_rows = (
        db.query(ArchitectureOptionRow)
        .filter(ArchitectureOptionRow.project_id == project_uuid)
        .order_by(ArchitectureOptionRow.fit_score.desc())
        .all()
    )
    options_payload = []
    for row in option_rows:
        design_raw = row.design if isinstance(getattr(row, "design", None), dict) else {}
        options_payload.append(
            {
                "id": str(row.id),
                "key": row.key,
                "title": row.title,
                "summary": row.summary,
                "pros": list(row.pros or []),
                "cons": list(row.cons or []),
                "fit_score": row.fit_score,
                "cost_band": row.cost_band,
                "ops_band": row.ops_band,
                "recommended": row.recommended,
                "selected": row.selected,
                "stack": list(row.stack or []),
                "design": design_raw,
            }
        )

    open_questions: list[str] = []
    try:
        from app.db.models import ClarificationQuestionRow

        open_qs = (
            db.query(ClarificationQuestionRow)
            .filter(
                ClarificationQuestionRow.project_id == project_uuid,
                ClarificationQuestionRow.status == "open",
            )
            .all()
        )
        open_questions = [f"{q.code}: {q.prompt}" for q in open_qs]
    except Exception:
        open_questions = []

    completeness_dict: dict = {}
    if completeness is not None:
        completeness_dict = {
            "overall": completeness.overall,
            "gaps": list(completeness.gaps or []),
            "missing_evidence": list(
                (quality_score or {}).get("missing_evidence") or []
            ),
        }

    documents = build_package_documents(
        ctx,
        tmpl,
        options=options_payload,
        backlog=backlog,
        adrs=adrs,
        risks=risks,
        citations=citation_dicts,
        quality_score=quality_score if isinstance(quality_score, dict) else {},
        hld_markdown=hld,
        executive_summary=ai_summary,
        open_questions=open_questions,
        completeness=completeness_dict,
        include_conditional=True,
    )
    documents["diagram_component"] = mermaid_component
    documents["diagram_dataflow"] = mermaid_dataflow

    prov = gateway.provenance(workflow_version="package.v8").model_dump()
    prov["retrieval_status"] = search.retrieval_status
    prov["ai_assist"] = ai_assist
    prov["artifact_catalog"] = "mvp.v2"
    prov["hld_source"] = hld_source
    prov["hld_model"] = hld_model
    if search.missing_sources:
        prov["retrieval_missing"] = search.missing_sources

    # Replace existing draft
    db.query(ArchitecturePackageRow).filter(
        ArchitecturePackageRow.project_id == project_uuid
    ).delete()
    pkg = ArchitecturePackageRow(
        id=uuid.uuid4(),
        project_id=project_uuid,
        option_id=selected.id,
        status="draft",
        hld_markdown=hld,
        mermaid=mermaid,
        mermaid_container=mermaid_container,
        mermaid_sequence=mermaid_sequence,
        mermaid_deploy=mermaid_deploy,
        adrs=adrs,
        risks=risks,
        backlog=backlog,
        epics=epics,
        threats=threats,
        quality_score=quality_score,
        citations=citation_dicts,
        documents=documents,
        retrieval_status=search.retrieval_status,
        ai_summary=ai_summary,
        provenance=prov,
    )
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    out = _package_out(pkg)

    # Keep the knowledge library current with designs and choices.
    # Capture failures must not poison this session or fail package generate.
    try:
        knowledge_service.capture_project_decision(
            db,
            project_name=ctx.name,
            project_id=project_id,
            option_title=tmpl.title,
            option_summary=tmpl.summary,
            adrs=list(adrs or []),
            risks=list(risks or []),
            backlog=list(backlog or []),
            quality_score=quality_score if isinstance(quality_score, dict) else None,
            hld_excerpt=(template_hld_for_excerpt or "")[:2500],
        )
    except Exception:
        db.rollback()
        logger.warning(
            "knowledge capture failed for project %s; package still returned",
            project_id,
            exc_info=True,
        )

    return (out, None)


def _package_out(pkg: ArchitecturePackageRow) -> PackageOut:
    assist = {}
    if isinstance(pkg.provenance, dict):
        assist = dict(pkg.provenance.get("ai_assist") or {})
    if not assist:
        assist = {"status": "skipped" if not pkg.ai_summary else "ok"}
    return PackageOut(
        id=str(pkg.id),
        status=pkg.status,
        option_id=str(pkg.option_id),
        hld_markdown=pkg.hld_markdown,
        mermaid=pkg.mermaid,
        mermaid_container=getattr(pkg, "mermaid_container", None) or "",
        mermaid_sequence=getattr(pkg, "mermaid_sequence", None) or "",
        mermaid_deploy=getattr(pkg, "mermaid_deploy", None) or "",
        adrs=[AdrOut.model_validate(a) for a in (pkg.adrs or [])],
        risks=[RiskOut.model_validate(r) for r in (pkg.risks or [])],
        citations=[
            CitationOut(
                document_id=c["document_id"],
                chunk_id=c["chunk_id"],
                title=c["title"],
                source_class=c["source_class"],
                citation=c["citation"],
                excerpt=c.get("excerpt") or (c.get("text") or "")[:280],
                score=float(c.get("score") or 0),
            )
            for c in (pkg.citations or [])
        ],
        quality_score=dict(getattr(pkg, "quality_score", None) or {}),
        backlog=list(getattr(pkg, "backlog", None) or []),
        epics=list(getattr(pkg, "epics", None) or []),
        threats=list(getattr(pkg, "threats", None) or []),
        documents=dict(getattr(pkg, "documents", None) or {}),
        retrieval_status=pkg.retrieval_status or "ok",
        ai_summary=pkg.ai_summary,
        ai_assist=assist,
        provenance=dict(pkg.provenance or {}),
    )


def get_package(db: Session, project_id: str) -> PackageOut | None:
    row = get_project_row(db, project_id)
    if row is None:
        return None
    pkg = (
        db.query(ArchitecturePackageRow)
        .filter(ArchitecturePackageRow.project_id == row.id)
        .order_by(ArchitecturePackageRow.created_at.desc())
        .first()
    )
    if pkg is None:
        return None
    return _package_out(pkg)
