"""Archavow API — S0."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.config import resolve_effective_ai_config
from app.auth import CurrentUser, get_current_user
from app.db.session import get_engine, get_session_factory
from app.modules import export as export_module
from app.modules import knowledge as knowledge_module
from app.modules import options as options_module
from app.modules import projects as projects_module
from app.modules import requirements as requirements_module
from app.modules import settings as settings_module
from app.modules.settings import service as settings_service

logger = logging.getLogger("archavow.api")

# Set during startup; health reports degraded when migrations did not reach head.
_SCHEMA_READY: bool = False
_SCHEMA_DETAIL: str = "not_checked"


def _startup() -> None:
    global _SCHEMA_READY, _SCHEMA_DETAIL
    # Models must be imported for metadata. Prefer Alembic; create_all is tests-only.
    import app.db.models  # noqa: F401
    from app.db.base import Base

    _SCHEMA_READY = False
    _SCHEMA_DETAIL = "pending"

    if os.environ.get("AUTO_MIGRATE", "true").lower() in {"1", "true", "yes"}:
        try:
            from alembic import command
            from alembic.config import Config

            cfg = Config("alembic.ini")
            db_url = os.environ.get("DATABASE_URL", "").strip()
            if db_url:
                cfg.set_main_option("sqlalchemy.url", db_url)
            command.upgrade(cfg, "head")
            _SCHEMA_READY = True
            _SCHEMA_DETAIL = "alembic_head"
        except Exception as exc:
            logger.exception("Alembic upgrade failed")
            _SCHEMA_READY = False
            _SCHEMA_DETAIL = f"alembic_failed:{exc.__class__.__name__}"
    else:
        _SCHEMA_DETAIL = "auto_migrate_disabled"

    if os.environ.get("AUTO_CREATE_TABLES", "false").lower() in {"1", "true", "yes"}:
        try:
            engine = get_engine()
            from sqlalchemy import text

            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            Base.metadata.create_all(bind=engine)
            # Dev/test escape hatch — tables exist even if Alembic was skipped/failed
            _SCHEMA_READY = True
            _SCHEMA_DETAIL = (
                "create_all"
                if _SCHEMA_DETAIL
                in {"auto_migrate_disabled", "pending", "create_all"}
                else f"{_SCHEMA_DETAIL}+create_all"
            )
        except Exception:
            logger.exception("AUTO_CREATE_TABLES failed; health will report postgres status")
            if not _SCHEMA_READY:
                _SCHEMA_DETAIL = "create_all_failed"

    if os.environ.get("AUTO_SEED_KNOWLEDGE", "true").lower() in {"1", "true", "yes"}:
        try:
            from app.modules.knowledge import service as knowledge_service

            SessionLocal = get_session_factory()
            db = SessionLocal()
            try:
                knowledge_service.ensure_seeded(db)
            finally:
                db.close()
        except Exception:
            logger.exception("AUTO_SEED_KNOWLEDGE failed; POST /knowledge/seed remains available")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _startup()
    yield


app = FastAPI(title="Archavow API", version="0.1.0", lifespan=lifespan)

_cors = [
    o.strip()
    for o in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:3001,http://127.0.0.1:3001",
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# When ARCHAVOW_API_KEY is set, every /api/v1 route requires Bearer auth.
# /health stays public. Stub mode remains when the key is unset (local only).
_require_user = [Depends(get_current_user)]
app.include_router(settings_module.router, dependencies=_require_user)
app.include_router(projects_module.router, dependencies=_require_user)
app.include_router(requirements_module.router, dependencies=_require_user)
app.include_router(options_module.router, dependencies=_require_user)
app.include_router(knowledge_module.router, dependencies=_require_user)
app.include_router(export_module.router, dependencies=_require_user)


@app.get("/api/v1/me")
def me(user: CurrentUser) -> dict:
    """Current principal — API key when ARCHAVOW_API_KEY is set, else local stub."""
    return {"data": user}


def _schema_ready(conn, dialect_name: str) -> bool:
    required = ("projects", "architecture_options", "architecture_packages")
    if dialect_name == "sqlite":
        from sqlalchemy import inspect

        insp = inspect(conn)
        return all(insp.has_table(name) for name in required)
    from sqlalchemy import text

    # Readiness derives from actual schema, not whether this process migrated
    row = conn.execute(
        text(
            "SELECT to_regclass('public.projects') IS NOT NULL "
            "AND to_regclass('public.architecture_options') IS NOT NULL "
            "AND to_regclass('public.architecture_packages') IS NOT NULL"
        )
    ).scalar()
    return bool(row)


def _probe_postgres() -> dict:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return {"ok": False, "detail": "DATABASE_URL not set", "schema_ready": False}
    try:
        # Do not reset_engine() here — that would wipe SQLite :memory: StaticPool DBs
        # used by unit tests. Callers that change DATABASE_URL must reset themselves.
        engine = get_engine()
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            schema_ready = _schema_ready(conn, engine.dialect.name)
            if not schema_ready:
                return {
                    "ok": False,
                    "detail": "connected_but_schema_incomplete",
                    "schema_ready": False,
                    "schema_detail": _SCHEMA_DETAIL,
                }
        return {
            "ok": True,
            "detail": "connected",
            "schema_ready": True,
            "schema_detail": _SCHEMA_DETAIL,
        }
    except Exception as exc:
        return {"ok": False, "detail": str(exc), "schema_ready": False}


@app.get("/health")
def health() -> dict:
    overrides: dict = {}
    try:
        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            overrides = settings_service.get_overrides(db)
        finally:
            db.close()
    except Exception:
        logger.debug("settings overrides unavailable for health", exc_info=True)
        overrides = {}

    cfg = resolve_effective_ai_config(overrides=overrides)
    postgres = _probe_postgres()
    status = "ok" if postgres.get("ok") else "degraded"
    return {
        "status": status,
        "postgres": postgres,
        "ai": {
            "chat_provider": cfg.chat_provider,
            "embedding_provider": cfg.embedding_provider,
            "chat_model": cfg.chat_model,
            "embedding_model": cfg.embedding_model,
            "openai_api_key_configured": cfg.openai_api_key_configured,
        },
    }
