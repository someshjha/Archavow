"""Delivery backlog: epics, user stories, and enabler stories.

The architecture backlog (`backlog.py`) answers "what must the architecture prove
before merge". This module answers "what does a delivery team pull into a sprint":
business epics with user stories written from the stated need, plus enabler stories
that carry the technical constraints (runtime, language, platform) which do not
belong inside a customer-facing story.

Every story traces back to the requirement text that justified it, so a reviewer
can ask "why is this in the backlog" and get an answer from the intake/interview
evidence rather than from the generator's imagination.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.modules.options.generator import OptionTemplate, ProjectContext

# Requirement classification. The theme with the most distinct keyword hits wins,
# because requirements borrow each other's vocabulary — "retain an audit trail for
# regulatory review" is about audit, not human review, and only the weight of
# evidence says so. List order breaks ties, so specific outcomes come before the
# broad decisioning theme ("approved claims must trigger a payment" is payment).
# Stems use `\w*` because a trailing `\b` after a stem never matches the inflected
# word — `adjudicat\b` cannot match "adjudicate".
_THEMES: list[tuple[str, str]] = [
    (
        "intake",
        r"\b(?:intake|submi\w*|upload\w*|captur\w*|ingest\w*|portal\w*|document\w*|attach\w*|fnol|forms?\b)",
    ),
    ("fraud", r"\b(?:fraud\w*|anomal\w*|suspicious|duplicat\w*|abuse|blacklist\w*)"),
    (
        "payment",
        r"\b(?:payment\w*|payout\w*|pay\b|settle\w*|disburs\w*|remit\w*|invoic\w*|refund\w*|reconcil\w*)",
    ),
    (
        "reporting",
        r"\b(?:report\w*|dashboard\w*|analytic\w*|metric\w*|kpi|insight\w*|volume\w*|cycle time)",
    ),
    (
        "audit",
        r"\b(?:audit\w*|complian\w*|regulat\w*|retention|retain\w*|gdpr|hipaa|pci|sox|traceab\w*|immutab\w*)",
    ),
    (
        "review",
        r"\b(?:review\w*|manual\w*|adjuster\w*|caseworker\w*|escalat\w*|exception\w*|override\w*|queue\w*)",
    ),
    (
        "decision",
        r"\b(?:adjudicat\w*|decision\w*|decid\w*|rules?\b|ruling\w*|approv\w*|reject\w*|eligib\w*|assess\w*|scor\w*|triag\w*|underwrit\w*)",
    ),
    (
        "status",
        r"\b(?:status\w*|notif\w*|track\w*|communicat\w*|email\w*|sms\b|self[- ]service|updates?\b)",
    ),
    (
        "integration",
        r"\b(?:integrat\w*|apis?\b|third[- ]party|external\w*|partner\w*|legacy|downstream|upstream)",
    ),
]

# Human-readable epic definitions keyed by theme.
_EPIC_SPECS: dict[str, dict[str, str]] = {
    "intake": {
        "title": "Submission intake",
        "need": "People and upstream systems need one reliable way to submit work with the data required to act on it.",
        "outcome": "Submissions arrive complete and validated, so downstream processing does not stall on missing data.",
        "actor": "submitter",
    },
    "decision": {
        "title": "Automated decisioning",
        "need": "Straightforward cases should be decided automatically so specialists spend their time on genuine exceptions.",
        "outcome": "A measurable share of cases is decided without human touch, with the reasoning recorded.",
        "actor": "operations lead",
    },
    "review": {
        "title": "Human review and exceptions",
        "need": "Cases the system cannot or must not decide alone need a clear path to a qualified human.",
        "outcome": "Exceptions reach the right person with full context and are resolved inside the agreed service level.",
        "actor": "reviewer",
    },
    "fraud": {
        "title": "Fraud and anomaly controls",
        "need": "Suspicious activity must be detected before value leaves the business.",
        "outcome": "High-risk cases are flagged and held for investigation with the signals that triggered them.",
        "actor": "investigator",
    },
    "payment": {
        "title": "Disbursement and settlement",
        "need": "Approved outcomes must convert into an accurate, traceable financial transaction.",
        "outcome": "Payments execute once, reconcile against the source case, and never silently duplicate.",
        "actor": "finance operator",
    },
    "status": {
        "title": "Status transparency",
        "need": "People chase updates when they cannot see progress for themselves.",
        "outcome": "Customers and staff can see current state without contacting support, cutting inbound queries.",
        "actor": "customer",
    },
    "integration": {
        "title": "System integration",
        "need": "The solution must exchange data with the systems that already hold the authoritative records.",
        "outcome": "Integrations are contract-tested and degrade predictably when a dependency is unavailable.",
        "actor": "integration owner",
    },
    "audit": {
        "title": "Audit and compliance evidence",
        "need": "Regulators and auditors require provable records of what happened and who decided it.",
        "outcome": "Every material action is reconstructable from an immutable trail within the retention window.",
        "actor": "compliance officer",
    },
    "reporting": {
        "title": "Operational reporting",
        "need": "Managers cannot improve throughput they cannot measure.",
        "outcome": "Volume, cycle time, and exception rates are visible to the people accountable for them.",
        "actor": "operations manager",
    },
    "core": {
        "title": "Core capability",
        "need": "The stated objective needs a working end-to-end path before anything else is worth building.",
        "outcome": "The primary flow works end to end for the main use case named in the objective.",
        "actor": "user",
    },
}

# Epic ordering: intake before decisioning before payout, supporting themes after.
_EPIC_ORDER = [
    "core",
    "intake",
    "decision",
    "review",
    "fraud",
    "payment",
    "status",
    "integration",
    "audit",
    "reporting",
]

_LANGUAGE_PATTERNS: list[tuple[str, str]] = [
    ("Java", r"\bjava\b(?!script)"),
    ("Kotlin", r"\bkotlin\b"),
    ("Python", r"\bpython\b"),
    ("TypeScript", r"\btypescript\b|\bnode(?:\.js)?\b"),
    ("C#", r"\bc#\b|\bdotnet\b|\b\.net\b"),
    ("Go", r"\bgo(?:lang)?\b"),
    ("Rust", r"\brust\b"),
]

_MEASURE_RE = re.compile(
    r"\d+\s*(?:%|percent|ms|s\b|sec|seconds|minutes?|hours?|days?|/s\b|per second|per day|k\b|rps|tps)",
    re.IGNORECASE,
)


def _requirement_theme(text: str) -> str:
    low = text.lower()
    best_theme = "core"
    best_score = 0
    for theme, pattern in _THEMES:
        score = len({m.group(0) for m in re.finditer(pattern, low)})
        if score > best_score:  # strict: first theme in list order wins ties
            best_theme, best_score = theme, score
    return best_theme


def _detect_languages(ctx: ProjectContext, option: OptionTemplate) -> list[str]:
    blob = " ".join(
        [ctx.tech_constraints, " ".join(option.stack), " ".join(ctx.requirements)]
    ).lower()
    found = [name for name, pattern in _LANGUAGE_PATTERNS if re.search(pattern, blob)]
    return found


def _shorten(text: str, limit: int = 120) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip(" ,.;:") + "…"


_MODAL = (
    r"must be able to|should be able to|must|should|shall|will|needs? to|"
    r"is able to|are able to|can"
)

# Subjects that are the solution itself. "I want the system to …" is the honest
# phrasing; pretending a person performs the action would misname the actor.
_SYSTEM_SUBJECTS = frozenset(
    {
        "system",
        "solution",
        "platform",
        "service",
        "application",
        "app",
        "product",
        "api",
        "it",
    }
)

_PERSON_WORDS = (
    r"claimant|customer|client|user|adjuster|assessor|underwriter|agent|broker|"
    r"caseworker|reviewer|approver|manager|operator|analyst|auditor|admin|"
    r"administrator|staff|employee|supplier|vendor|partner|applicant|patient|"
    r"student|driver|merchant|investigator|team|lead|owner|officer"
)


def _singular(noun: str) -> str:
    low = noun.strip().lower()
    if low.endswith(("ss", "us", "is", "sis")) or not low.endswith("s"):
        return low
    if low.endswith("ies"):
        return low[:-3] + "y"
    return low[:-1]


def _lower_first(text: str) -> str:
    """Lower-case the opening letter, unless the first word is an acronym.

    Requirements often start with one ("PDF exports must…", "RTO must be…") and
    blindly lowering produced "pDF exports".
    """
    if not text:
        return text
    first = text.split(" ", 1)[0]
    if any(c.isupper() for c in first[1:]):
        return text
    return text[:1].lower() + text[1:]


@dataclass
class _StoryPhrase:
    """The grammatical pieces needed to write one story from one requirement."""

    actor: str
    goal: str
    # person: the actor performs the goal. system: the actor wants the system to
    # do it. other: a named thing must do it ("approved claims must …").
    shape: str
    subject: str = ""

    @property
    def wants(self) -> str:
        if self.shape == "person":
            return f"I want to {self.goal}"
        if self.shape == "system":
            return f"I want the system to {self.goal}"
        return f"I need {self.subject} to {self.goal}"

    @property
    def trigger(self) -> str:
        """The When clause: who or what sets the behaviour off."""
        if self.shape == "person":
            return f"they {self.goal}"
        if self.shape == "system":
            return f"the system is asked to {self.goal}"
        # Restoring the modal keeps the passive requirement readable as a When
        # clause: "straightforward claims must be adjudicated automatically".
        return f"{self.subject} must {self.goal}"


# Article choice follows sound, not spelling: "a user", "an hour".
_TAKES_A = re.compile(r"^(?:u(?:se|ni|ti|sa)|eu|one)", re.IGNORECASE)
_TAKES_AN = re.compile(r"^(?:hour|honest|honou?r)", re.IGNORECASE)


def article_for(noun: str) -> str:
    if _TAKES_AN.match(noun):
        return "an"
    if _TAKES_A.match(noun):
        return "a"
    return "an" if noun[:1].lower() in "aeiou" else "a"


def _story_phrase(requirement: str, default_actor: str) -> _StoryPhrase:
    clean = " ".join(requirement.split()).rstrip(".")
    # Split on the modal wherever it falls. Anchoring a bounded subject pattern
    # to the start fails on real requirements ("Claims above 5,000 or with
    # missing evidence must be routed…") and silently produced broken titles.
    match = re.search(rf"\s+(?:{_MODAL})\s+", clean, flags=re.IGNORECASE)
    if match and match.start() > 0:
        subject = clean[: match.start()].strip()
        goal = _lower_first(clean[match.end() :].strip())
        subject_low = re.sub(r"^the\s+", "", subject.lower())
        head = _singular(subject_low.split()[-1]) if subject_low.split() else ""
        if head in _SYSTEM_SUBJECTS:
            return _StoryPhrase(default_actor, _shorten(goal), "system")
        if re.fullmatch(rf"(?:\w+\s+)*(?:{_PERSON_WORDS})s?", subject_low):
            return _StoryPhrase(_singular(subject_low), _shorten(goal), "person")
        # Match on the lower-cased subject, but display the original casing so
        # acronyms survive ("PDF summaries", not "pdf summaries").
        subject_text = _lower_first(re.sub(r"^[Tt]he\s+", "", subject).strip())
        return _StoryPhrase(
            default_actor, _shorten(goal), "other", subject=_shorten(subject_text, 70)
        )

    goal = re.sub(rf"^(?:we\s+)?(?:{_MODAL})\s+", "", clean, flags=re.IGNORECASE)
    goal = re.sub(r"^(?:support|provide|enable|allow)\s+", "", goal, flags=re.IGNORECASE)
    return _StoryPhrase(default_actor, _shorten(_lower_first(goal)), "person")


def _outcome_clause(outcome: str) -> str:
    """First clause of the epic outcome — the rest turns the title into a paragraph."""
    clean = " ".join(outcome.split()).rstrip(".")
    clean = re.split(r",\s*(?:so|which|and then)\b|;", clean, maxsplit=1)[0]
    return _lower_first(clean.strip())


def _acceptance_for(phrase: _StoryPhrase, theme: str) -> list[dict]:
    """Given/When/Then scenarios: one happy path, one failure/edge path."""
    actor = phrase.actor
    art = article_for(actor)
    given = (
        f"{art} {actor} with a valid, complete submission"
        if theme in {"intake", "core"}
        else f"{art} {actor} and a case that meets the stated conditions"
    )
    happy = {
        "id": "AC-1",
        "given": given,
        "when": phrase.trigger,
        "then": "the action succeeds, the resulting state is persisted, and the outcome is visible to the people accountable for it",
    }
    if theme in {"decision", "fraud"}:
        edge = {
            "id": "AC-2",
            "given": "a case that falls outside the automated decision rules",
            "when": "the rules are evaluated",
            "then": "the case is routed to human review with the triggering signals recorded, and no automated outcome is applied",
        }
    elif theme == "payment":
        edge = {
            "id": "AC-2",
            "given": "a disbursement that has already been executed for the case",
            "when": "the same disbursement is submitted again",
            "then": "the duplicate is rejected idempotently and the original transaction reference is returned",
        }
    elif theme == "integration":
        edge = {
            "id": "AC-2",
            "given": "the downstream system of record is unavailable",
            "when": "the integration is called",
            "then": "the request is retried within policy, the caller receives an explicit degraded response, and no data is lost",
        }
    elif theme in {"audit", "review"}:
        edge = {
            "id": "AC-2",
            "given": "a completed action on a case",
            "when": "an auditor inspects the case history",
            "then": "actor, timestamp, inputs, and decision reason are present and immutable",
        }
    else:
        edge = {
            "id": "AC-2",
            "given": "a submission that fails validation",
            "when": f"the {actor} submits it",
            "then": "the specific invalid fields are reported, nothing partial is persisted, and they can correct and resubmit",
        }
    return [happy, edge]


def _nfr_checks(ctx: ProjectContext, theme: str) -> list[str]:
    checks: list[str] = []
    targets = " ".join([ctx.scale_availability or "", " ".join(ctx.requirements)])
    measured = _MEASURE_RE.findall(targets)
    if ctx.scale_availability and measured:
        checks.append(f"Meets the stated targets: {_shorten(ctx.scale_availability, 90)}")
    else:
        checks.append("Performance target agreed with the product owner before this story is closed")
    if theme in {"payment", "audit", "decision", "fraud"}:
        checks.append("Action is recorded in the audit trail with actor, timestamp, and reason")
    if theme in {"intake", "status"}:
        checks.append("Accessible to keyboard and screen-reader users (WCAG 2.1 AA)")
    return checks


def _business_stories(
    theme: str,
    spec: dict[str, str],
    requirements: list[tuple[int, str]],
    ctx: ProjectContext,
    start_index: int,
) -> list[dict]:
    stories: list[dict] = []
    outcome = _outcome_clause(spec["outcome"])
    for offset, (req_index, req_text) in enumerate(requirements):
        phrase = _story_phrase(req_text, spec["actor"])
        article = article_for(phrase.actor)
        stories.append(
            {
                "id": f"US-{start_index + offset:03d}",
                "type": "business",
                "title": f"As {article} {phrase.actor}, {phrase.wants} so that {outcome}",
                "actor": phrase.actor,
                "need": spec["need"],
                "priority": "P0" if theme in {"core", "intake", "decision"} else "P1",
                "requirement_refs": [f"R-{req_index:03d}"],
                "requirement_texts": [_shorten(req_text, 200)],
                "acceptance_criteria": _acceptance_for(phrase, theme),
                "nfr_checks": _nfr_checks(ctx, theme),
                "dependencies": [],
                "origin": "evidence_derived",
            }
        )
    return stories


def _enabler_stories(ctx: ProjectContext, option: OptionTemplate) -> list[dict]:
    """Technical work that constrains how stories get built.

    Implementation language, runtime and platform belong here — a customer-facing
    story should not mention Java or Kubernetes.

    Enablers carry their own EN-001… sequence rather than continuing the US
    counter, so neither series has gaps.
    """
    languages = _detect_languages(ctx, option)
    stack = ", ".join(option.stack) or "the selected stack"
    stories: list[dict] = []
    index = 1

    if languages:
        primary = languages[0]
        secondary = ", ".join(languages[1:])
        goal = f"scaffold the services in {primary}"
        if secondary:
            goal += f" (with {secondary} where it is already the team's tool)"
        stories.append(
            {
                "id": f"EN-{index:03d}",
                "type": "enabler",
                "title": f"As a delivery team, we need to {goal} so that every story is implemented on one agreed runtime",
                "actor": "delivery team",
                "need": (
                    f"{primary} was named as the implementation language, so the build, test, "
                    "and deployment toolchain must be settled before feature work starts."
                ),
                "priority": "P0",
                "requirement_refs": [],
                "requirement_texts": [],
                "acceptance_criteria": [
                    {
                        "id": "AC-1",
                        "given": f"a new service in the {primary} template",
                        "when": "a developer runs the standard build and test commands",
                        "then": "the service builds, tests pass, and a deployable artifact is produced by CI",
                    }
                ],
                "nfr_checks": ["Language and runtime versions pinned and recorded in the ADR log"],
                "dependencies": [],
            }
        )
        index += 1
    else:
        stories.append(
            {
                "id": f"EN-{index:03d}",
                "type": "enabler",
                "title": "As a delivery team, we need to agree the implementation language and runtime so that estimates and hiring are grounded",
                "actor": "delivery team",
                "need": (
                    "No implementation language was evidenced in intake or the interview. "
                    "Leaving it open makes every story estimate speculative."
                ),
                "priority": "P0",
                "requirement_refs": [],
                "requirement_texts": [],
                "acceptance_criteria": [
                    {
                        "id": "AC-1",
                        "given": "the shortlisted languages and the team's current skills",
                        "when": "the architect and tech lead review them against the selected option",
                        "then": "one primary language is chosen, written into an ADR, and the decision is dated",
                    }
                ],
                "nfr_checks": ["Decision captured as an ADR before sprint 1 planning"],
                "dependencies": [],
            }
        )
        index += 1

    stories.append(
        {
            "id": f"EN-{index:03d}",
            "type": "enabler",
            "title": f"As a delivery team, we need a deployable walking skeleton on {stack} so that integration risk surfaces in week one",
            "actor": "delivery team",
            "need": (
                f"{option.title} depends on {stack}. A thin end-to-end slice proves the pieces "
                "connect before feature stories assume they do."
            ),
            "priority": "P0",
            "requirement_refs": [],
            "requirement_texts": [],
            "acceptance_criteria": [
                {
                    "id": "AC-1",
                    "given": "the walking skeleton deployed to a non-production environment",
                    "when": "a request traverses the full path end to end",
                    "then": "it succeeds and emits traces, logs, and metrics from every hop",
                }
            ],
            "nfr_checks": ["Deployment is automated and repeatable from CI"],
            "dependencies": ["EN-001"],
        }
    )
    index += 1

    stories.append(
        {
            "id": f"EN-{index:03d}",
            "type": "enabler",
            "title": "As a delivery team, we need authentication and authorization on every write path so that no story ships an open endpoint",
            "actor": "delivery team",
            "need": (
                "Auth applied per-story drifts. Establishing it once as a platform concern keeps "
                "every later story compliant by default."
            ),
            "priority": "P0",
            "requirement_refs": [],
            "requirement_texts": [],
            "acceptance_criteria": [
                {
                    "id": "AC-1",
                    "given": "an unauthenticated request to any write endpoint",
                    "when": "the request reaches the gateway or the service directly",
                    "then": "it is rejected with 401, and the rejection is logged",
                }
            ],
            "nfr_checks": ["Covered by automated tests on write paths"],
            "dependencies": ["EN-001"],
        }
    )
    for story in stories:
        story["origin"] = "baseline_recommendation"
    return stories


def build_epics(ctx: ProjectContext, option: OptionTemplate) -> list[dict]:
    """Group evidenced requirements into epics with traceable stories.

    Returns [] when there are no requirements to trace — an empty delivery backlog
    is honest, whereas invented epics would look like evidence.
    """
    requirements = [
        (i + 1, " ".join(r.split()))
        for i, r in enumerate(ctx.stated_requirements)
        if str(r).strip()
    ]
    if not requirements:
        return []

    grouped: dict[str, list[tuple[int, str]]] = {}
    for index, text in requirements:
        grouped.setdefault(_requirement_theme(text), []).append((index, text))

    epics: list[dict] = []
    story_index = 1
    epic_index = 1
    for theme in _EPIC_ORDER:
        items = grouped.get(theme)
        if not items:
            continue
        spec = _EPIC_SPECS[theme]
        stories = _business_stories(theme, spec, items, ctx, story_index)
        story_index += len(stories)
        epics.append(
            {
                "id": f"E-{epic_index:03d}",
                "title": spec["title"],
                "need": spec["need"],
                "business_outcome": spec["outcome"],
                "priority": "P0" if theme in {"core", "intake", "decision"} else "P1",
                "requirement_refs": [f"R-{i:03d}" for i, _ in items],
                "origin": "evidence_derived",
                "stories": stories,
            }
        )
        epic_index += 1

    enablers = _enabler_stories(ctx, option)
    epics.append(
        {
            "id": f"E-{epic_index:03d}",
            "title": "Technical enablers",
            "need": (
                "Cross-cutting technical decisions and platform work that every business "
                "story depends on. Kept separate so user stories stay about user outcomes. "
                "These are baseline recommendations, not evidence-derived backlog items."
            ),
            "business_outcome": (
                "Feature teams start on a proven runtime with auth, deployment, and "
                "observability already in place."
            ),
            "priority": "P0",
            "requirement_refs": [],
            "origin": "baseline_recommendation",
            "stories": enablers,
        }
    )
    return epics
