"""Data models for requirements gap detection."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.requirements.answer_checks import answer_satisfies
from app.modules.requirements.scorecard import CategoryScore, UnlockCheck


@dataclass
class IntakeSnapshot:
    business_objective: str = ""
    problem_statement: str = ""
    preferred_cloud: str = ""
    scale_availability: str = ""
    tech_constraints: str = ""
    requirement_texts: list[str] = field(default_factory=list)
    # Requirements the human stated at intake, excluding rows derived from
    # interview answers. Story-readiness gaps read this instead of the full list:
    # answering one question must not silently close a different question just
    # because the answer text was filed as a requirement.
    intake_requirement_texts: list[str] = field(default_factory=list)
    # code -> answer text; only evidence-valid answers close gaps
    answered_answers: dict[str, str] = field(default_factory=dict)

    @property
    def answered_codes(self) -> set[str]:
        return {
            code
            for code, text in self.answered_answers.items()
            if answer_satisfies(code, text)
        }


@dataclass
class Gap:
    code: str
    prompt: str
    category: str  # requirements | nfrs | security


@dataclass
class Completeness:
    """Scorecard for one project: five buckets plus the options gate.

    `categories` is the source of truth; the flat per-category fields exist so
    callers can read one number without walking the list.
    """

    overall: int
    scope: int
    story_readiness: int
    reliability: int
    security_compliance: int
    delivery: int
    categories: list[CategoryScore] = field(default_factory=list)
    ready: bool = False
    unlock: list[UnlockCheck] = field(default_factory=list)


@dataclass
class GapAnalysis:
    gaps: list[Gap]
    captured: list[str]
    completeness: Completeness
