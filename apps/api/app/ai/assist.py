"""Optional AI assist helpers — always safe to call; never break deterministic flows.

This module is kept as a thin backward-compatible re-export. The
implementation now lives in sibling modules:
- assist_status.py — AiAssistStatus, as_ai_failure
- assist_interview.py — interview rewrite/acknowledge/suggest/follow-up flows
- assist_package.py — package executive-summary enrichment
- assist_options.py — architecture options generation
"""

from __future__ import annotations

from app.ai.assist_interview import (
    InterviewAssistResult,
    _normalize_followup_item,
    acknowledge_answer,
    assist_interview,
    suggest_answer_draft,
)
from app.ai.assist_options import generate_architecture_options
from app.ai.assist_package import enrich_package_summary
from app.ai.assist_status import AiAssistStatus, as_ai_failure

__all__ = [
    "AiAssistStatus",
    "as_ai_failure",
    "InterviewAssistResult",
    "assist_interview",
    "acknowledge_answer",
    "suggest_answer_draft",
    "enrich_package_summary",
    "generate_architecture_options",
    # Private helper still imported directly by tests.
    "_normalize_followup_item",
]
