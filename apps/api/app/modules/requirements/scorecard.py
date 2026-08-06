"""Interview completeness scorecard — categories, gate, and question ordering.

Owns the interview's canonical code order and the five buckets those codes roll
up into. Kept separate from gap analysis so the gate (`is_ready`) and the
lifecycle agree on one definition of "the interview is done enough".
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

# Canonical order for interview question codes (solution-shaping first, then
# story readiness, then NFR/security). Used for checks iteration, deterministic
# result ordering, and as the tie-break when two categories are equally weak.
CODE_ORDER: list[str] = [
    "current_approach",
    "functional_scope",
    # Story-readiness codes: without these the delivery backlog cannot produce
    # user stories with a real actor, rule, edge case, or measure of done.
    "user_roles",
    "business_rules",
    "exception_handling",
    "success_metrics",
    "implementation_language",
    "integrations",
    "team_constraints",
    "rto_rpo",
    "peak_traffic",
    "data_residency",
    "auth_model",
    "consistency",
    "cloud",
]

CODE_LABELS: dict[str, str] = {
    "current_approach": "current approach",
    "functional_scope": "functional scope",
    "user_roles": "user roles",
    "business_rules": "business rules",
    "exception_handling": "exception handling",
    "success_metrics": "success metrics",
    "implementation_language": "implementation language",
    "integrations": "integrations",
    "team_constraints": "team constraints",
    "rto_rpo": "RTO / RPO",
    "peak_traffic": "peak traffic",
    "data_residency": "data residency",
    "auth_model": "auth model",
    "consistency": "system of record",
    "cloud": "cloud / regions",
}


@dataclass(frozen=True)
class ScoreCategory:
    key: str
    label: str
    codes: tuple[str, ...]
    # Minimum score this bucket must reach before options unlock. A floor per
    # category stops one strong bucket from carrying an empty one.
    floor: int


CATEGORIES: tuple[ScoreCategory, ...] = (
    ScoreCategory(
        key="scope",
        label="Scope",
        codes=("current_approach", "functional_scope", "integrations"),
        floor=50,
    ),
    # Highest floor: thin story evidence produces thin epics, and the delivery
    # backlog is generated straight from these answers.
    ScoreCategory(
        key="story_readiness",
        label="Story readiness",
        codes=("user_roles", "business_rules", "exception_handling", "success_metrics"),
        floor=75,
    ),
    ScoreCategory(
        key="reliability",
        label="Reliability",
        codes=("rto_rpo", "peak_traffic", "consistency"),
        floor=50,
    ),
    ScoreCategory(
        key="security_compliance",
        label="Security & compliance",
        codes=("auth_model", "data_residency"),
        floor=50,
    ),
    ScoreCategory(
        key="delivery",
        label="Delivery",
        codes=("implementation_language", "team_constraints", "cloud"),
        floor=50,
    ),
)

OVERALL_FLOOR = 70
OVERALL_LABEL = "Overall"

_CATEGORY_BY_CODE: dict[str, ScoreCategory] = {
    code: category for category in CATEGORIES for code in category.codes
}
_CODE_RANK: dict[str, int] = {code: idx for idx, code in enumerate(CODE_ORDER)}


@dataclass
class CategoryScore:
    key: str
    label: str
    score: int
    floor: int
    closed: int
    total: int
    open_codes: list[str] = field(default_factory=list)

    @property
    def open_labels(self) -> list[str]:
        return [code_label(code) for code in self.open_codes]


@dataclass
class UnlockCheck:
    """One condition standing between the current answers and architecture options."""

    key: str  # category key, or "overall"
    label: str
    value: int
    target: int
    ok: bool


@dataclass
class Projection:
    """What closing one more question would do to the scorecard."""

    category_key: str
    category_label: str
    category_from: int
    category_to: int
    overall_from: int
    overall_to: int


def category_for_code(code: str) -> ScoreCategory | None:
    """Bucket a question code belongs to, or None for AI follow-ups."""
    return _CATEGORY_BY_CODE.get(code)


def code_label(code: str) -> str:
    return CODE_LABELS.get(code, code.replace("_", " "))


def _percent(closed: int, total: int) -> int:
    if total <= 0:
        return 100
    return round(100 * closed / total)


def score_categories(satisfied: Mapping[str, bool]) -> list[CategoryScore]:
    """Score each bucket as the share of its codes that are closed.

    A code missing from `satisfied` counts as open, so a caller that only
    reports closures still gets an honest score.
    """
    scores: list[CategoryScore] = []
    for category in CATEGORIES:
        open_codes = [code for code in category.codes if not satisfied.get(code, False)]
        closed = len(category.codes) - len(open_codes)
        scores.append(
            CategoryScore(
                key=category.key,
                label=category.label,
                score=_percent(closed, len(category.codes)),
                floor=category.floor,
                closed=closed,
                total=len(category.codes),
                open_codes=open_codes,
            )
        )
    return scores


def overall_score(categories: Sequence[CategoryScore]) -> int:
    """Unweighted mean of the category scores.

    Deliberately not weighted by code count: the two-code Security bucket moves
    the overall number as much as the four-code Story readiness bucket.
    """
    if not categories:
        return 100
    return round(sum(c.score for c in categories) / len(categories))


def unlock_checks(categories: Sequence[CategoryScore], overall: int) -> list[UnlockCheck]:
    checks = [
        UnlockCheck(
            key=c.key,
            label=c.label,
            value=c.score,
            target=c.floor,
            ok=c.score >= c.floor,
        )
        for c in categories
    ]
    checks.append(
        UnlockCheck(
            key="overall",
            label=OVERALL_LABEL,
            value=overall,
            target=OVERALL_FLOOR,
            ok=overall >= OVERALL_FLOOR,
        )
    )
    return checks


def is_ready(categories: Sequence[CategoryScore], overall: int) -> bool:
    """Whether the interview clears the gate for architecture options.

    Every category must reach its floor and the overall must reach 70. Closing
    every question implies all of that, so there is no separate "zero gaps"
    shortcut — overall ≥ 70 on its own is not enough either, which is what used
    to let an empty Security bucket through.
    """
    return all(check.ok for check in unlock_checks(categories, overall))


def failing_checks(categories: Sequence[CategoryScore], overall: int) -> list[UnlockCheck]:
    return [check for check in unlock_checks(categories, overall) if not check.ok]


def pick_next_code(
    open_codes: Sequence[str], category_scores: Mapping[str, int]
) -> str | None:
    """Next question to ask: from the weakest category, then in CODE_ORDER.

    Returns None when no open code belongs to a category (e.g. only AI
    follow-ups remain), leaving the choice to the caller.
    """
    ranked: list[tuple[int, int, str]] = []
    for code in open_codes:
        category = category_for_code(code)
        if category is None:
            continue
        score = category_scores.get(category.key, 0)
        ranked.append((score, _CODE_RANK.get(code, len(CODE_ORDER)), code))
    if not ranked:
        return None
    ranked.sort()
    return ranked[0][2]


def project_close(code: str, categories: Sequence[CategoryScore]) -> Projection | None:
    """Scorecard movement from closing `code`, or None if it changes nothing.

    Exact rather than approximate: a code is either closed or open, so one
    answer always moves its category by a fixed step.
    """
    category = category_for_code(code)
    if category is None:
        return None
    current = next((c for c in categories if c.key == category.key), None)
    if current is None or current.closed >= current.total:
        return None

    after = _percent(current.closed + 1, current.total)
    overall_before = overall_score(categories)
    projected = [
        CategoryScore(
            key=c.key,
            label=c.label,
            score=after if c.key == current.key else c.score,
            floor=c.floor,
            closed=c.closed + 1 if c.key == current.key else c.closed,
            total=c.total,
            open_codes=[x for x in c.open_codes if x != code],
        )
        for c in categories
    ]
    return Projection(
        category_key=current.key,
        category_label=current.label,
        category_from=current.score,
        category_to=after,
        overall_from=overall_before,
        overall_to=overall_score(projected),
    )
