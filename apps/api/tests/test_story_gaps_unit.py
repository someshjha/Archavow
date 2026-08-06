"""Story-readiness interview gaps (roles, rules, exceptions, metrics, language)."""

from __future__ import annotations

from app.modules.requirements.gap_analyze import analyze_gaps
from app.modules.requirements.gap_models import IntakeSnapshot

_STORY_CODES = {
    "user_roles",
    "business_rules",
    "exception_handling",
    "success_metrics",
    "implementation_language",
}


def _codes(snap: IntakeSnapshot) -> set[str]:
    return {g.code for g in analyze_gaps(snap).gaps}


def test_bare_project_opens_every_story_gap() -> None:
    assert _STORY_CODES <= _codes(IntakeSnapshot())


def test_stated_requirements_close_the_gaps_they_evidence() -> None:
    reqs = [
        "Claimants submit claims and adjusters review the exceptions they cannot decide.",
        "Auto-approve claims under 5,000 when validation passes; anything above goes to a reviewer.",
        "Invalid submissions are rejected with the failing fields and nothing is persisted.",
        "Target 60% straight-through processing with median cycle time under 10 minutes.",
    ]
    snap = IntakeSnapshot(
        requirement_texts=reqs,
        intake_requirement_texts=reqs,
        tech_constraints="Java 21 with Spring Boot",
    )
    assert not (_STORY_CODES & _codes(snap))


def test_interview_derived_requirements_do_not_close_story_gaps() -> None:
    """Answering one question must not silently close a different one.

    Interview answers are filed as requirements, so if story gaps read the full
    requirement list, an answer about roles could satisfy the exceptions gap by
    accident and the interview would skip a question nobody answered.
    """
    answer_text = (
        "Claimants submit claims and adjusters review the exceptions they cannot decide."
    )
    snap = IntakeSnapshot(
        requirement_texts=[answer_text],  # filed from an interview answer
        intake_requirement_texts=[],  # nothing stated at intake
        answered_answers={"user_roles": answer_text},
    )
    codes = _codes(snap)
    assert "user_roles" not in codes  # closed by its own answer
    assert "exception_handling" in codes  # not closed by another question's answer


def test_vague_answers_do_not_close_story_gaps() -> None:
    snap = IntakeSnapshot(
        answered_answers={
            "user_roles": "all kinds of users, the usual ones",
            "business_rules": "the normal business rules apply",
            "exception_handling": "we handle errors properly",
            "success_metrics": "it should be fast and reliable",
            "implementation_language": "whatever the team prefers",
        }
    )
    assert _STORY_CODES <= _codes(snap)


def test_concrete_answers_close_story_gaps() -> None:
    snap = IntakeSnapshot(
        answered_answers={
            "user_roles": "Claimant submits, adjuster reviews exceptions, auditor reads history",
            "business_rules": "Rules: auto-approve under 5,000 on clean validation, else a human decides",
            "exception_handling": "Invalid input is rejected with failing fields; failed calls retry then queue for manual review",
            "success_metrics": "60% straight-through, median cycle time under 10 minutes",
            "implementation_language": "Java 21 with Spring Boot",
        }
    )
    assert not (_STORY_CODES & _codes(snap))


def test_language_named_in_tech_constraints_is_not_asked_again() -> None:
    snap = IntakeSnapshot(tech_constraints="Python 3.12, FastAPI, Postgres")
    assert "implementation_language" not in _codes(snap)
