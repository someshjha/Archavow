"""Architecture option generation, listing, and selection."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.ai.assist import generate_architecture_options
from app.ai.assist_status import AI_PROVIDER_ERRORS
from app.ai.config import resolve_effective_ai_config
from app.db.models import ArchitectureOptionRow, ArchitecturePackageRow, RequirementRow
from app.modules.options.generator import (
    OptionTemplate,
    ProjectContext,
    generate_option_templates,
)
from app.modules.options.schemas import OptionOut
from app.modules.projects.service import get_project_row
from app.modules.settings import service as settings_service

logger = logging.getLogger("archavow.options")

_TEMPLATE_SUMMARY_PREFIX = "[Starter template] "


def _design_out(row: ArchitectureOptionRow):
    from app.modules.options.schemas import OptionDesignOut

    raw = row.design if isinstance(getattr(row, "design", None), dict) else {}
    return OptionDesignOut(
        approach=str(raw.get("approach") or "").strip(),
        assumptions=[str(a).strip() for a in (raw.get("assumptions") or []) if str(a).strip()],
        constraints=[str(c).strip() for c in (raw.get("constraints") or []) if str(c).strip()],
        key_decisions=[
            str(d).strip() for d in (raw.get("key_decisions") or []) if str(d).strip()
        ],
    )


def _opt_out(row: ArchitectureOptionRow) -> OptionOut:
    return OptionOut(
        id=str(row.id),
        key=row.key,
        title=row.title,
        summary=row.summary,
        pros=list(row.pros or []),
        cons=list(row.cons or []),
        fit_score=row.fit_score,
        cost_band=row.cost_band,
        ops_band=row.ops_band,
        recommended=row.recommended,
        selected=row.selected,
        stack=list(row.stack or []),
        origin=row.origin if row.origin in {"template", "ai"} else "template",
        design=_design_out(row),
    )


def _context(db: Session, project_id: str) -> tuple[ProjectContext, uuid.UUID] | None:
    row = get_project_row(db, project_id)
    if row is None:
        return None
    rows = (
        db.query(RequirementRow)
        .filter(RequirementRow.project_id == row.id)
        .order_by(RequirementRow.created_at.asc())
        .all()
    )
    ctx = ProjectContext(
        name=row.name,
        preferred_cloud=row.preferred_cloud or "",
        tech_constraints=row.tech_constraints or "",
        scale_availability=row.scale_availability or "",
        business_objective=row.business_objective or "",
        problem_statement=row.problem_statement or "",
        requirements=[r.text for r in rows],
        stated_requirements=[r.text for r in rows if r.source == "intake"],
    )
    return ctx, row.id


def _options_payload(db: Session, project_uuid: uuid.UUID) -> dict:
    rows = (
        db.query(ArchitectureOptionRow)
        .filter(ArchitectureOptionRow.project_id == project_uuid)
        .order_by(ArchitectureOptionRow.fit_score.desc())
        .all()
    )
    selected = next((r for r in rows if r.selected), None)
    return {
        "options": [_opt_out(r) for r in rows],
        "selected_option_id": str(selected.id) if selected else None,
    }


def generate_options(db: Session, project_id: str) -> dict | None:
    parsed = _context(db, project_id)
    if parsed is None:
        return None
    ctx, project_uuid = parsed

    # Serialize generate/swap against concurrent generate + select + package mutate
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
        return None

    # Build replacements first — never delete existing rows until we have three ready
    ai_assist = {"status": "skipped", "detail": None}
    templates: list[OptionTemplate] = []
    try:
        cfg = resolve_effective_ai_config(overrides=settings_service.get_overrides(db))
        gateway = _service.build_gateway(cfg)
        templates, status = generate_architecture_options(gateway, ctx)
        ai_assist = status.model_dump()
        for t in templates:
            t.origin = "ai"
    except AI_PROVIDER_ERRORS as exc:
        templates = []
        ai_assist = {"status": "failed", "detail": str(exc)[:200]}
    # Unexpected bugs (AttributeError, KeyError, …) propagate — do not polish them
    # into a successful template generation.
    if len(templates) != 3:
        templates = generate_option_templates(ctx)
        for t in templates:
            t.origin = "template"
        if ai_assist.get("status") != "failed":
            ai_assist = {
                "status": "failed" if ai_assist.get("status") == "failed" else "skipped",
                "detail": ai_assist.get("detail") or "deterministic_fallback",
            }
        else:
            ai_assist = {
                "status": "failed",
                "detail": f"{ai_assist.get('detail')};deterministic_fallback",
            }

    if len(templates) != 3:
        # Leave existing options intact if we still cannot produce a replacement set
        logger.error("option generation produced %s templates; aborting swap", len(templates))
        payload = _options_payload(db, project_uuid)
        payload["ai_assist"] = {
            "status": "failed",
            "detail": "replacement_set_incomplete",
        }
        return payload

    new_rows = [
        ArchitectureOptionRow(
            id=uuid.uuid4(),
            project_id=project_uuid,
            key=tmpl.key,
            title=tmpl.title,
            summary=_persist_summary(tmpl),
            pros=list(tmpl.pros),
            cons=list(tmpl.cons),
            fit_score=tmpl.fit_score,
            cost_band=tmpl.cost_band,
            ops_band=tmpl.ops_band,
            recommended=tmpl.recommended,
            selected=False,
            stack=list(tmpl.stack),
            design=tmpl.design_dict(),
            origin=tmpl.origin if tmpl.origin in {"template", "ai"} else "template",
        )
        for tmpl in templates
    ]

    # Single transaction: delete old package/options, insert replacements
    try:
        db.query(ArchitecturePackageRow).filter(
            ArchitecturePackageRow.project_id == project_uuid
        ).delete()
        db.query(ArchitectureOptionRow).filter(
            ArchitectureOptionRow.project_id == project_uuid
        ).delete()
        for row in new_rows:
            db.add(row)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("option swap failed for project %s", project_id)
        raise

    payload = _options_payload(db, project_uuid)
    payload["ai_assist"] = ai_assist
    return payload


def _persist_summary(tmpl: OptionTemplate) -> str:
    text = (tmpl.summary or "").strip()
    if tmpl.origin == "template" and not text.startswith(_TEMPLATE_SUMMARY_PREFIX.strip()):
        return f"{_TEMPLATE_SUMMARY_PREFIX}{text}"
    return text


def list_options(db: Session, project_id: str) -> dict | None:
    row = get_project_row(db, project_id)
    if row is None:
        return None
    return _options_payload(db, row.id)


def select_option(db: Session, project_id: str, option_id: str) -> dict | None:
    row = get_project_row(db, project_id)
    if row is None:
        return None
    try:
        oid = uuid.UUID(option_id)
    except ValueError:
        return None

    from app.db.models import ProjectRow

    locked = (
        db.query(ProjectRow)
        .filter(ProjectRow.id == row.id)
        .with_for_update()
        .first()
    )
    if locked is None:
        return None

    # Serialize concurrent selects for this project
    options = (
        db.query(ArchitectureOptionRow)
        .filter(ArchitectureOptionRow.project_id == row.id)
        .with_for_update()
        .all()
    )
    # Compare as strings so Uuid/str dialect differences never miss a row.
    option = next((o for o in options if str(o.id) == str(oid)), None)
    if option is None:
        return None

    already_selected = bool(option.selected)
    # Clear first so the partial unique index never sees two selected rows mid-flush
    db.query(ArchitectureOptionRow).filter(
        ArchitectureOptionRow.project_id == row.id,
        ArchitectureOptionRow.selected.is_(True),
    ).update({"selected": False}, synchronize_session="fetch")
    option.selected = True
    db.add(option)
    # Clear packages only when the human gate choice actually changes
    if not already_selected:
        db.query(ArchitecturePackageRow).filter(
            ArchitecturePackageRow.project_id == row.id
        ).delete()
    db.commit()
    return _options_payload(db, row.id)
