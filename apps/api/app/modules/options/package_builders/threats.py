"""STRIDE-lite threat sketch for the package build step."""

from __future__ import annotations

from app.modules.options.generator import OptionTemplate, ProjectContext
from app.modules.options.package_builders._shared import _domain_terms, _stack_flags


def build_threats(ctx: ProjectContext, option: OptionTemplate) -> list[dict]:
    """STRIDE-lite threat sketch — only for assets we can justify from stack/constraints."""
    flags = _stack_flags(ctx, option)
    terms = _domain_terms(ctx)
    threats: list[dict] = []
    n = 1

    def add(**kwargs: str) -> None:
        nonlocal n
        row = {"id": f"T-{n:03d}", **kwargs}
        row.setdefault("controls", row.get("mitigation", ""))
        row.setdefault("unresolved", "")
        row.setdefault("privacy", "")
        threats.append(row)
        n += 1

    if flags["api_edge"]:
        add(
            stride="Spoofing",
            asset="API edge",
            boundary="Client → edge",
            threat=f"Someone pretends to be {terms['caller']} and slips in {terms['forged']}.",
            mitigation="mTLS or signed tokens at the edge; no anonymous writes.",
            controls="Edge authn/z, token validation, deny-by-default routes",
            unresolved="Caller identity model still fuzzy if interview left auth open",
            privacy="Tokens must not log PII claims in clear text",
        )
        add(
            stride="Denial of Service",
            asset="API edge / app runtime",
            boundary="Client → edge",
            threat="A traffic spike knocks over the edge or the app before anything useful happens.",
            mitigation="Rate limits, autoscaling, and back-pressure on writes.",
            controls="Rate limits, HPA/autoscaling, load-shed policies",
            unresolved="",
            privacy="",
        )
    if flags["datastore"]:
        add(
            stride="Tampering",
            asset="System of record",
            boundary="App → database",
            threat=f"A fat service account quietly rewrites {terms['state']} with no audit trail.",
            mitigation="Least-privilege DB roles, append-only audit, CDC if you need forensics.",
            controls="Least-privilege roles, audit trail, encryption at rest",
            unresolved="Data classification / retention not always captured yet",
            privacy="Confirm whether stored fields include PII/regulated data",
        )
    if flags["messaging"]:
        add(
            stride="Information Disclosure",
            asset="Message bus",
            boundary="App → messaging",
            threat=terms["disclose"],
            mitigation="Tight ACLs, encrypt the sensitive fields, keep retention honest.",
            controls="Topic ACLs, field-level encryption, retention caps",
            unresolved="",
            privacy="Payloads may carry PII — classify topics before broad consume rights",
        )
        add(
            stride="Repudiation",
            asset="Message bus",
            boundary="Producer → broker",
            threat=terms["repudiation"],
            mitigation="Idempotent producers, broker audit logs, correlation IDs in the payload.",
            controls="Producer idempotency, broker audit, correlation IDs",
            unresolved="",
            privacy="",
        )
    if flags["containers"]:
        add(
            stride="Elevation of Privilege",
            asset="Container runtime",
            boundary="Cluster → node",
            threat="A compromised pod runs as root or with privileged capabilities.",
            mitigation="Pod security standards, non-root, drop caps; run the K8s checker.",
            controls="PSS/PSA, non-root, dropped capabilities, network policy",
            unresolved="",
            privacy="",
        )
    elif flags["serverless"]:
        add(
            stride="Elevation of Privilege",
            asset="Serverless runtime",
            boundary="Platform → function",
            threat="An over-powered execution role turns one function into a lateral-move trampoline.",
            mitigation="Least-privilege roles, secret isolation, platform identity binding.",
            controls="Least-privilege roles, secret isolation, identity binding",
            unresolved="",
            privacy="",
        )

    if not threats:
        add(
            stride="Information Disclosure",
            asset="Application surface",
            boundary="Unspecified — stack still thin",
            threat=(
                "Not enough stack detail to sketch concrete STRIDE assets. "
                "This is a sticky note, not a threat model."
            ),
            mitigation="Name the runtime, data store, and edge in the interview, then regenerate.",
            controls="None yet — insufficient asset inventory",
            unresolved="Full threat model blocked on stack evidence",
            privacy="Cannot assess privacy boundaries until data stores are named",
        )
    return threats
