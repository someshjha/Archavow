"""Advisor: compare two architecture options and accept a choice as an ADR (human gate #2)."""

from __future__ import annotations

import re
import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import ArchitectureOptionRow, ArchitecturePackageRow
from app.modules.options.service import AdrOut
from app.modules.projects.service import get_project_row

_ADR_ID_RE = re.compile(r"^ADR-(\d+)$")


class AdvisorAcceptIn(BaseModel):
    option_id_a: str
    option_id_b: str
    chosen_option_id: str
    rationale: str = ""


def _next_adr_id(adrs: list[dict]) -> str:
    highest = 0
    for adr in adrs:
        match = _ADR_ID_RE.match(str(adr.get("id", "")))
        if match:
            highest = max(highest, int(match.group(1)))
    return f"ADR-{highest + 1:03d}"


def accept_comparison(
    db: Session, project_id: str, body: AdvisorAcceptIn
) -> tuple[AdrOut | None, list[AdrOut] | None, str | None]:
    """Returns (new_adr, all_adrs, error). error in {'not_found', 'invalid_options', 'package_not_found'}."""
    row = get_project_row(db, project_id)
    if row is None:
        return None, None, "not_found"

    try:
        oid_a = uuid.UUID(body.option_id_a)
        oid_b = uuid.UUID(body.option_id_b)
        chosen_id = uuid.UUID(body.chosen_option_id)
    except ValueError:
        return None, None, "invalid_options"
    if chosen_id not in (oid_a, oid_b):
        return None, None, "invalid_options"

    options = {
        o.id: o
        for o in db.query(ArchitectureOptionRow)
        .filter(
            ArchitectureOptionRow.project_id == row.id,
            ArchitectureOptionRow.id.in_([oid_a, oid_b]),
        )
        .all()
    }
    if oid_a not in options or oid_b not in options:
        return None, None, "invalid_options"

    chosen_row = options[chosen_id]
    other_row = options[oid_b if chosen_id == oid_a else oid_a]

    pkg = (
        db.query(ArchitecturePackageRow)
        .filter(ArchitecturePackageRow.project_id == row.id)
        .with_for_update()
        .order_by(ArchitecturePackageRow.created_at.desc())
        .first()
    )
    if pkg is None:
        return None, None, "package_not_found"

    adrs = list(pkg.adrs or [])
    rationale = (body.rationale or "").strip()
    adr = {
        "id": _next_adr_id(adrs),
        "title": f"Confirm {chosen_row.title} over {other_row.title}",
        "status": "accepted",
        "context": rationale
        or (
            f"Compared against {other_row.title} "
            f"(fit {other_row.fit_score}, cost {other_row.cost_band}, ops {other_row.ops_band})."
        ),
        "decision": (
            f"Keep **{chosen_row.title}** (fit {chosen_row.fit_score}, "
            f"cost {chosen_row.cost_band}, ops {chosen_row.ops_band}) over {other_row.title}."
        ),
        "consequences": [
            *[f"Advantage: {p}" for p in list(chosen_row.pros or [])[:2]],
            *[f"Foregone: {p}" for p in list(other_row.pros or [])[:2]],
        ],
    }
    adrs.append(adr)
    pkg.adrs = adrs
    db.add(pkg)
    db.commit()
    db.refresh(pkg)

    out_adrs = [AdrOut(**a) for a in (pkg.adrs or [])]
    new_adr = next(a for a in out_adrs if a.id == adr["id"])
    return new_adr, out_adrs, None
