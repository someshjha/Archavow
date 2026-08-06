"""Deterministic NFR / requirements gap detection for S1 interview.

This module is kept as a thin backward-compatible re-export. The
implementation now lives in sibling modules:
- gap_models.py — IntakeSnapshot, Gap, Completeness, GapAnalysis
- answer_checks.py — placeholder detection + answer satisfaction checks
- gap_analyze.py — analyze_gaps + intake evidence helpers
- scorecard.py — completeness categories, options gate, question ordering
"""

from __future__ import annotations

from app.modules.requirements.answer_checks import (
    SUGGESTION_TEMPLATES,
    answer_satisfies,
    is_placeholder_answer,
    kind_from_category,
    matches_suggestion_template,
    suggestion_template,
)
from app.modules.requirements.gap_analyze import CODE_ORDER, analyze_gaps
from app.modules.requirements.gap_models import Completeness, Gap, GapAnalysis, IntakeSnapshot
from app.modules.requirements.scorecard import (
    CATEGORIES,
    CategoryScore,
    Projection,
    UnlockCheck,
    category_for_code,
    code_label,
    pick_next_code,
    project_close,
)

__all__ = [
    "IntakeSnapshot",
    "Gap",
    "Completeness",
    "GapAnalysis",
    "CODE_ORDER",
    "CATEGORIES",
    "CategoryScore",
    "UnlockCheck",
    "Projection",
    "analyze_gaps",
    "category_for_code",
    "code_label",
    "pick_next_code",
    "project_close",
    "answer_satisfies",
    "is_placeholder_answer",
    "suggestion_template",
    "matches_suggestion_template",
    "kind_from_category",
    "SUGGESTION_TEMPLATES",
]
