"""Placeholder detection + evidence-satisfaction checks for interview answers."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.requirements.gap_models import IntakeSnapshot

_PLACEHOLDER_ANSWERS = frozenset(
    {
        "tbd",
        "tba",
        "tbc",
        "n/a",
        "na",
        "n.a.",
        "none",
        "unknown",
        "not discussed",
        "not discussed yet",
        "standard scale",
        "high",
        "medium",
        "low",
        "normal",
        "todo",
        "yes",
        "no",
        "ok",
        "okay",
        "-",
        "—",
        ".",
    }
)

# Phrases that invalidate an otherwise keyword-matching answer
_PLACEHOLDER_PHRASE_RE = re.compile(
    r"(?:"
    r"\btbd\b|"
    r"\btba\b|"
    r"\btbc\b|"
    r"\bn/?a\b|"
    r"\bn\.a\.\b|"
    r"\bunknown\b|"
    r"\bpending\b|"
    r"\bplaceholder\b|"
    r"\bdummy\b|"
    r"\blorem ipsum\b|"
    r"\bxxx+\b|"
    r"\btodo\b|"
    r"\bfill[- ]?in\b|"
    r"\bcoming soon\b|"
    r"\bnot sure\b|"
    r"\bnot yet\b|"
    r"\bnot discussed\b|"
    r"\bto be (?:decided|determined|defined|discussed|confirmed|agreed)\b|"
    r"\bwill (?:decide|define|confirm|discuss) later\b|"
    r"\bas above\b|"
    r"\bsee above\b|"
    r"\bsee intake\b|"
    r"\btest(?:ing)? answer\b|"
    r"\bfor now\b.*\b(?:tbd|unknown|pending)\b|"
    r"\bsomehow\b|"
    r"\bwhatever\b"
    r")",
    re.IGNORECASE,
)


def is_placeholder_answer(text: str) -> bool:
    """True when the whole answer is empty/placeholder, or embeds placeholder phrases."""
    cleaned = (text or "").strip().lower()
    if not cleaned:
        return True
    if cleaned in _PLACEHOLDER_ANSWERS:
        return True
    if re.fullmatch(r"[\-—./\s]+", cleaned):
        return True
    if _PLACEHOLDER_PHRASE_RE.search(cleaned):
        return True
    return False


def _has(blob: str, *patterns: str) -> bool:
    return any(re.search(p, blob, re.I) for p in patterns)


def _text_has_peak_load(text: str) -> bool:
    """Concrete throughput/concurrency signals — not placeholder scale text."""
    scale = (text or "").strip()
    if not scale or is_placeholder_answer(scale):
        return False
    scale_l = scale.lower()
    keywords = (
        "peak",
        "tps",
        "events/sec",
        "events/s",
        "throughput",
        "/sec",
        "qps",
        "rps",
        "m/",
        "k/",
        "concurrent",
        "concurrency",
    )
    if any(k in scale_l for k in keywords):
        return True
    if re.search(r"\d", scale) and any(
        k in scale_l
        for k in ("event", "request", "req", "user", "transaction", "msg", "message", "row")
    ):
        return True
    return _has(
        scale_l,
        r"events?/s(?:ec)?",
        r"\brps\b",
        r"\bqps\b",
        r"\btps\b",
        r"throughput\s*[:=]?\s*\d",
        r"peak\s+\d",
        r"concurren\w*\s*[:=]?\s*\d",
    )


def answer_satisfies(code: str, text: str) -> bool:
    """Whether an interview answer provides enough evidence to close a gap.

    Bare keyword mentions (e.g. \"jwt\", \"postgres\", \"region\") are not enough —
    answers must include concrete decision content for the question.
    """
    if is_placeholder_answer(text):
        return False
    cleaned = (text or "").strip()
    blob = cleaned.lower()
    # Strip trivial wrappers so \"OIDC.\" / \"postgres!\" still count as bare
    compact = re.sub(r"[^\w\s/+.-]+", " ", blob)
    compact = re.sub(r"\s+", " ", compact).strip()

    if code.startswith("ai_"):
        return len(cleaned) >= 24

    if code == "peak_traffic":
        return _text_has_peak_load(cleaned)

    if code == "user_roles":
        # A named role, not "users" in the abstract — "all kinds of users" tells a
        # story writer nothing about who the actor is.
        if not _has(
            blob,
            r"\b(?:claimant|customer|client|adjuster|assessor|underwriter|agent|broker|"
            r"caseworker|reviewer|approver|manager|operator|analyst|auditor|admin|"
            r"administrator|staff|employee|supplier|vendor|partner|applicant|patient|"
            r"student|driver|merchant|role|persona|actor)\w*",
        ):
            return False
        return len(cleaned) >= 16

    if code == "business_rules":
        # The word "rule" is neither necessary nor sufficient: "the normal business
        # rules apply" states nothing, while "auto-approve claims under 5,000" is a
        # rule without the word. Require an outcome verb plus a condition.
        if not _has(
            blob,
            r"\bapprov\w*",
            r"\breject\w*",
            r"\bdeclin\w*",
            r"\bdecid\w*",
            r"\bdecision\w*",
            r"\badjudicat\w*",
            r"\broute\w*",
            r"\bescalat\w*",
            r"\bflag\w*",
            r"\bhold\w*",
            r"\beligib\w*",
            r"\bqualif\w*",
            r"\bpric\w*",
            r"\bcalculat\w*",
        ):
            return False
        if not _has(
            blob,
            r"\d",
            r"\bif\b",
            r"\bwhen\b",
            r"\bunless\b",
            r"\botherwise\b",
            r"\belse\b",
            r"\bcriteri",
            r"\bthreshold",
            r"\beligib",
            r"\bautomatic\w*",
            r"\broute\w*",
            r"\bescalat\w*",
        ):
            return False
        return len(cleaned) >= 24

    if code == "exception_handling":
        # Naming the failure is half an answer; the response to it is the half a
        # story needs ("we handle errors properly" describes no behaviour).
        if not _has(
            blob,
            r"\bfail\w*",
            r"\berrors?\b",
            r"\bexceptions?\b",
            r"\btime\s?out\w*",
            r"\binvalid\b",
            r"\bunavailable\b",
            r"\bdown\b",
            r"\bmissing\b",
            r"\bwrong\b",
        ):
            return False
        if not _has(
            blob,
            r"\bretr(?:y|ies|ied)\b",
            r"\bfall\s?back\b",
            r"\bqueue\w*",
            r"\bmanual\w*",
            r"\bescalat\w*",
            r"\breject\w*",
            r"\broll\s?back\w*",
            r"\bdead[- ]letter\w*",
            r"\bcompensat\w*",
            r"\bresubmit\w*",
            r"\balert\w*",
            r"\bnotif\w*",
            r"\bhuman\b",
            r"\breview\w*",
        ):
            return False
        return len(cleaned) >= 24

    if code == "success_metrics":
        # A measure of done needs a number and a unit, not an adjective.
        if not re.search(
            r"\d+\s*(?:%|percent|ms\b|s\b|sec\w*|min\w*|hour\w*|day\w*|week\w*|"
            r"claims?|cases?|requests?|users?|tickets?|calls?|k\b|/\s*\w+)",
            blob,
        ):
            return False
        return len(cleaned) >= 12

    if code == "implementation_language":
        if not _has(
            blob,
            r"\bjava\b(?!script)",
            r"\bkotlin\b",
            r"\bpython\b",
            r"\btypescript\b",
            r"\bjavascript\b",
            r"\bnode(?:\.js)?\b",
            r"\bc#\b",
            r"\b\.net\b",
            r"\bdotnet\b",
            r"\bgo(?:lang)?\b",
            r"\brust\b",
            r"\bscala\b",
            r"\bruby\b",
            r"\bphp\b",
            r"\bswift\b",
            r"\bc\+\+\b",
        ):
            return False
        return len(cleaned) >= 8

    if code == "rto_rpo":
        # Both targets with numeric values required (not just the words RTO/RPO)
        has_rto = re.search(r"\brto\b[^.\n]{0,48}\d", blob)
        has_rpo = re.search(r"\brpo\b[^.\n]{0,48}\d", blob)
        return bool(has_rto and has_rpo)

    if code == "data_residency":
        # Must mention residency/sovereignty/GDPR concretely — not \"not required\" alone
        if not _has(blob, r"residenc", r"sovereign", r"gdpr", r"data region", r"data\s+local"):
            return False
        return len(cleaned) >= 16

    if code == "auth_model":
        # Require a named mechanism plus decision context — not a bare token in a stack list
        if not re.search(
            r"(?:"
            r"(?:oauth2?|oidc|m?tls|jwt|saml|sso|rbac|api[_ ]?keys?)\b"
            r"[^.\n]{0,80}"
            r"(?:via|with|using|through|entra|okta|keycloak|cognito|auth0|"
            r"client|partner|gateway|issuer|token|flow|provider)|"
            r"(?:authenticate|authentication|authn)\b[^.\n]{0,60}\w{3,}"
            r")",
            blob,
        ):
            return False
        bare = {
            "oauth",
            "oauth2",
            "oauth 2",
            "mtls",
            "api key",
            "apikey",
            "api_key",
            "oidc",
            "jwt",
            "saml",
            "rbac",
            "sso",
            "authentication",
            "authenticate",
        }
        if compact in bare:
            return False
        return len(cleaned) >= 16

    if code == "consistency":
        # Require an explicit SoR / authoritative-store decision, not a tech token
        if _has(
            blob,
            r"system of record",
            r"authoritative\s+(?:store|source|database|db|state|system)",
            r"\bis\s+(?:the\s+)?(?:system of record|authoritative)",
            r"exactly[- ]?once",
        ):
            return len(cleaned) >= 16
        return False

    if code == "cloud":
        providers = (
            r"\bazure\b",
            r"\baws\b",
            r"\bgcp\b",
            r"google\s*cloud",
            r"\boci\b",
            r"on[- ]?prem(?:ise)?",
        )
        if not _has(blob, *providers):
            return False
        # Reject provider-only or \"region\"-only answers
        if compact in {
            "azure",
            "aws",
            "gcp",
            "oci",
            "google cloud",
            "onprem",
            "on-prem",
            "on premise",
            "region",
        }:
            return False
        return len(cleaned) >= 10

    # Unknown deterministic codes: require substantive free text
    return len(cleaned) >= 24


def _cloud_template(snap: IntakeSnapshot) -> str:
    provider = snap.preferred_cloud.strip()
    if provider:
        return (
            f"State the cloud/regions in scope. Intake currently says {provider} — "
            "confirm or correct that, and say whether multi-region is required."
        )
    return "State the cloud provider and regions in scope, and whether multi-region is required."


# Prompt-shaped drafts only — never invent SLOs, team sizes, or controls.
# The interview UI presents these as editable drafts; verbatim submit is rejected.
SUGGESTION_TEMPLATES: dict[str, str | Callable[[IntakeSnapshot], str]] = {
    "current_approach": (
        "Describe how this is handled today (manual process, legacy system, or nothing yet)."
    ),
    "functional_scope": (
        "List the must-have user flows and features for this system (not nice-to-haves)."
    ),
    "user_roles": (
        "Name each distinct role that uses this system and what each role needs to accomplish."
    ),
    "business_rules": (
        "State the rules/policies that decide outcomes, including when a human must decide."
    ),
    "exception_handling": (
        "Describe what happens on invalid input, dependency failure, or undecidable cases."
    ),
    "success_metrics": (
        "State the measurable targets that mean this worked (include the numbers you care about)."
    ),
    "implementation_language": (
        "Name the language and runtime to build in, and note team strengths if they constrain that."
    ),
    "integrations": (
        "List the systems, data stores, or APIs this must integrate with or replace."
    ),
    "team_constraints": (
        "State team size/skills and timeline constraints that rule technologies in or out."
    ),
    "rto_rpo": "State RTO and RPO for primary-region failure (with units).",
    "peak_traffic": "State sustained and peak throughput or concurrency the system must sustain.",
    "data_residency": (
        "State any data residency or sovereignty rules, or say explicitly that none apply."
    ),
    "auth_model": (
        "Describe how clients and services authenticate and authorize (name the actual controls)."
    ),
    "consistency": (
        "Name the system of record for authoritative state and what is derived vs authoritative."
    ),
    "cloud": _cloud_template,
}


def suggestion_template(code: str, snap: IntakeSnapshot) -> str | None:
    """Deterministic draft answer for a gap code — used when AI assist is unavailable."""
    tmpl = SUGGESTION_TEMPLATES.get(code)
    if tmpl is None:
        return None
    return tmpl(snap) if callable(tmpl) else tmpl


def matches_suggestion_template(code: str, answer: str, snap: IntakeSnapshot) -> bool:
    """True when the answer is an unedited suggestion template for this code."""
    tmpl = suggestion_template(code, snap)
    if not tmpl:
        return False
    return " ".join(answer.split()).lower() == " ".join(tmpl.split()).lower()


def kind_from_category(category: str) -> str:
    """Map interview question category → requirement kind."""
    mapping = {
        "requirements": "fr",
        "nfrs": "nfr",
        "security": "security",
    }
    return mapping.get((category or "").strip().lower(), "other")
