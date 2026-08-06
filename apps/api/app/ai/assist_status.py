"""AI assist status helpers — map provider errors to a safe, typed status."""

from __future__ import annotations

import json
import logging
from typing import Literal

import httpx
from pydantic import BaseModel

from app.ai.gateway import EmptyAIResponseError, EmbeddingDisabledError
from app.ai.json_schema import SchemaValidationError, UnsupportedSchemaError
from app.ai.providers.openai_chat import OpenAIRefusalError

logger = logging.getLogger(__name__)

# Provider/network failures degrade to status=failed. Programming defects re-raise.
AI_PROVIDER_ERRORS: tuple[type[BaseException], ...] = (
    EmptyAIResponseError,
    EmbeddingDisabledError,
    OpenAIRefusalError,
    UnsupportedSchemaError,
    SchemaValidationError,
    TimeoutError,
    ConnectionError,
    OSError,
    httpx.HTTPError,
    json.JSONDecodeError,
)


class AiAssistStatus(BaseModel):
    status: Literal["ok", "skipped", "failed"] = "skipped"
    detail: str | None = None


def as_ai_failure(exc: BaseException) -> AiAssistStatus:
    """Map expected AI/provider errors to failed status; re-raise unexpected bugs."""
    if isinstance(exc, AI_PROVIDER_ERRORS):
        return AiAssistStatus(status="failed", detail=str(exc)[:200])
    logger.exception("Unexpected error in AI assist path: %s", exc)
    raise exc
