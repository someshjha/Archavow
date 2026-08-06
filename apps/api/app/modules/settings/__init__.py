"""Settings AI HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.ai.schemas import AISettingsUpdate, ChatModelRef, EffectiveAIConfig, ProbeResult
from app.ai.url_safety import UnsafeAIBaseURLError, assert_safe_ai_base_url
from app.auth import CurrentUser
from app.db.session import get_db
from app.modules.settings import service as settings_service

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class AISettingsPatchBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chat_provider: str | None = None
    chat_model: str | None = Field(default=None, max_length=128)
    embedding_provider: str | None = None
    embedding_model: str | None = Field(default=None, max_length=128)
    embedding_dimensions: int | None = Field(default=None, ge=768, le=768)
    ollama_base_url: str | None = None
    openai_base_url: str | None = None
    openai_api_key: str | None = Field(default=None, exclude=True)
    hld_fallback_chain: list[ChatModelRef] | None = Field(default=None, max_length=4)


@router.get("/ai")
def get_ai_settings(_user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    cfg: EffectiveAIConfig = settings_service.get_effective_ai_settings(db)
    return {"data": cfg.model_dump()}


@router.patch("/ai")
def patch_ai_settings(
    body: AISettingsPatchBody,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> dict:
    raw = body.model_dump(exclude={"openai_api_key"}, exclude_none=True)
    for key in ("ollama_base_url", "openai_base_url"):
        if key in raw and raw[key]:
            try:
                raw[key] = assert_safe_ai_base_url(str(raw[key]))
            except UnsafeAIBaseURLError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
    update = AISettingsUpdate(**raw)
    cfg = settings_service.update_ai_settings(db, update)
    return {"data": cfg.model_dump()}


@router.post("/ai/probe/chat")
def probe_chat(_user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    try:
        cfg = settings_service.get_effective_ai_settings(db)
        base = cfg.ollama_base_url if cfg.chat_provider == "ollama" else cfg.openai_base_url
        assert_safe_ai_base_url(base)
    except UnsafeAIBaseURLError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result: ProbeResult = settings_service.probe_chat(db)
    return {"data": result.model_dump()}


@router.post("/ai/probe/embeddings")
def probe_embeddings(_user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    try:
        cfg = settings_service.get_effective_ai_settings(db)
        if cfg.embedding_provider == "ollama":
            assert_safe_ai_base_url(cfg.ollama_base_url)
        elif cfg.embedding_provider == "openai":
            assert_safe_ai_base_url(cfg.openai_base_url)
    except UnsafeAIBaseURLError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result: ProbeResult = settings_service.probe_embeddings(db)
    return {"data": result.model_dump()}
