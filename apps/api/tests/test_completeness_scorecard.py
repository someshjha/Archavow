"""Interview completeness scorecard — buckets, options gate, question ordering."""

from __future__ import annotations

from app.modules.requirements.scorecard import (
    CATEGORIES,
    CODE_ORDER,
    is_ready,
    overall_score,
    pick_next_code,
    project_close,
    score_categories,
    unlock_checks,
)


def _all_closed(except_codes: set[str] | None = None) -> dict[str, bool]:
    skip = except_codes or set()
    return {code: code not in skip for code in CODE_ORDER}


def _by_key(categories):  # type: ignore[no-untyped-def]
    return {c.key: c for c in categories}


def test_every_question_code_belongs_to_exactly_one_category() -> None:
    seen: list[str] = [code for category in CATEGORIES for code in category.codes]
    assert sorted(seen) == sorted(CODE_ORDER)
    assert len(seen) == len(set(seen))


def test_category_score_is_share_of_closed_codes() -> None:
    cats = _by_key(score_categories(_all_closed({"business_rules", "auth_model"})))
    assert cats["story_readiness"].score == 75
    assert cats["story_readiness"].open_codes == ["business_rules"]
    assert cats["security_compliance"].score == 50
    assert cats["scope"].score == 100


def test_small_bucket_moves_overall_as_much_as_large_one() -> None:
    """Overall is an unweighted mean, so a 2-code bucket is not cheap to skip."""
    without_security = overall_score(
        score_categories(_all_closed({"auth_model", "data_residency"}))
    )
    without_scope = overall_score(
        score_categories(
            _all_closed({"current_approach", "functional_scope", "integrations"})
        )
    )
    assert without_security == without_scope == 80


def test_high_overall_alone_does_not_unlock_options() -> None:
    """The old loophole: overall ≥ 70 with an empty Security bucket."""
    cats = score_categories(_all_closed({"auth_model", "data_residency"}))
    overall = overall_score(cats)
    assert overall >= 70
    assert is_ready(cats, overall) is False
    failing = [c.key for c in unlock_checks(cats, overall) if not c.ok]
    assert failing == ["security_compliance"]


def test_story_readiness_needs_three_of_four_codes() -> None:
    two_open = score_categories(_all_closed({"business_rules", "exception_handling"}))
    assert is_ready(two_open, overall_score(two_open)) is False

    one_open = score_categories(_all_closed({"business_rules"}))
    assert _by_key(one_open)["story_readiness"].score == 75
    assert is_ready(one_open, overall_score(one_open)) is True


def test_ready_when_every_floor_and_overall_are_met() -> None:
    cats = score_categories(_all_closed())
    assert overall_score(cats) == 100
    assert is_ready(cats, 100) is True
    assert all(c.ok for c in unlock_checks(cats, 100))


def test_next_question_comes_from_the_weakest_category() -> None:
    # Scope nearly done, Security untouched — ask Security next even though
    # scope codes sort earlier in CODE_ORDER.
    cats = score_categories(
        _all_closed({"integrations", "auth_model", "data_residency"})
    )
    scores = {c.key: c.score for c in cats}
    assert pick_next_code(["integrations", "auth_model", "data_residency"], scores) == (
        "data_residency"
    )


def test_equally_weak_categories_fall_back_to_code_order() -> None:
    scores = {c.key: 0 for c in CATEGORIES}
    assert pick_next_code(["auth_model", "current_approach", "rto_rpo"], scores) == (
        "current_approach"
    )


def test_ai_followups_have_no_category_and_defer_to_the_caller() -> None:
    scores = {c.key: 50 for c in CATEGORIES}
    assert pick_next_code(["ai_extra_1", "ai_extra_2"], scores) is None


def test_projection_reports_the_exact_step_an_answer_is_worth() -> None:
    cats = score_categories(_all_closed({"auth_model", "data_residency", "peak_traffic"}))
    projection = project_close("auth_model", cats)
    assert projection is not None
    assert (projection.category_from, projection.category_to) == (0, 50)
    assert projection.overall_from == overall_score(cats)
    assert projection.overall_to == projection.overall_from + 10


def test_projection_is_none_for_closed_or_unknown_codes() -> None:
    cats = score_categories(_all_closed())
    assert project_close("auth_model", cats) is None
    assert project_close("ai_followup_1", cats) is None
