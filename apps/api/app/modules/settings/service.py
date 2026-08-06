"""Workspace AI settings — Postgres-backed overrides."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai.config import resolve_effective_ai_config
from app.ai.gateway import build_gateway
from app.ai.schemas import AISettingsUpdate, EffectiveAIConfig, ProbeResult
from app.db.models import WorkspaceSettingsRow

SINGLETON_ID = 1


def _ensure_row(db: Session) -> WorkspaceSettingsRow:
    row = db.get(WorkspaceSettingsRow, SINGLETON_ID)
    if row is None:
        row = WorkspaceSettingsRow(id=SINGLETON_ID, ai_overrides={})
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_overrides(db: Session) -> dict[str, Any]:
    row = _ensure_row(db)
    return dict(row.ai_overrides or {})


def reset_overrides(db: Session) -> None:
    row = _ensure_row(db)
    row.ai_overrides = {}
    db.add(row)
    db.commit()


def get_effective_ai_settings(db: Session) -> EffectiveAIConfig:
    return resolve_effective_ai_config(overrides=get_overrides(db))


def update_ai_settings(db: Session, update: AISettingsUpdate) -> EffectiveAIConfig:
    payload = update.model_dump(exclude_unset=True)
    payload.pop("openai_api_key", None)
    row = _ensure_row(db)
    merged = dict(row.ai_overrides or {})
    for key, value in payload.items():
        if value is not None:
            merged[key] = value
    row.ai_overrides = merged
    db.add(row)
    db.commit()
    db.refresh(row)
    return get_effective_ai_settings(db)


def probe_chat(db: Session) -> ProbeResult:
    cfg = get_effective_ai_settings(db)
    return build_gateway(cfg).probe_chat()


def probe_embeddings(db: Session) -> ProbeResult:
    cfg = get_effective_ai_settings(db)
    return build_gateway(cfg).probe_embeddings()
