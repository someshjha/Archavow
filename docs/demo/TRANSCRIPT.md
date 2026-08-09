# Archavow final walkthrough

> **Status:** this transcript was rewritten against a live run of the redesigned UI (persistent left rail, Evidence & Coverage panel, options matrix, requirement ledger, package/export screens) using the real **Claims Intake & Automated Adjudication** demo project, provider = OpenAI (`gpt-4o-mini` chat, `text-embedding-3-small` embeddings — confirmed via `/health`). Every line below is a direct transcription of what actually rendered, not a script written in advance. It was used as the shot list for [`archavow-final-demo.mp4`](archavow-final-demo.mp4).

## 1. Projects

The workspace opens on a table, not a card grid: **Name / Stage / Progress / actions**. The demo project shows:

```
Claims Intake & Automated Adjudication   AZURE KAFKA SPRING-BOOT KUBERNETES
Stage: EXPORT   Progress: 7/7   [Continue] [Dashboard] [Delete]
```

Left rail: **Archavow** wordmark, then **Projects / Knowledge / Settings**. No project is open yet, so there's no stage rail or Evidence panel — those appear once you're inside a project.

## 2. Create the project (Onboarding)

`+ Start onboarding` → **Load demo scenario** fills the form instantly: objective, problem statement, cloud (Azure), scale targets, tech constraints (Java 21, Spring Boot, Kafka, AKS, Postgres, Entra ID).

The requirements section is a live ledger, not a textarea. **Load demo scenario** populates it with ten rows, each already numbered:

```
R-001  Claimants must submit a claim online with supporting documents and photos.
R-002  The system must validate the policy is active and covers the claimed loss before adjudication.
R-003  Straightforward claims must be adjudicated automatically against the published rules.
R-004  Claims above 5,000 or with missing evidence must be routed to a human adjuster with the reason.
R-005  Suspicious or duplicate claims must be flagged and held for investigation.
R-006  Approved claims must trigger a payment to the claimant's verified account exactly once.
R-007  Claimants must be able to see the current status of their claim without calling support.
R-008  The system must integrate with the existing policy administration system as the system of record.
R-009  Every decision must retain an immutable audit trail for seven years for regulatory review.
R-010  Operations managers must see claim volume, cycle time, and exception rates daily.

10 requirements captured.
```

**Save & start interview** commits the project.

## 3. Close evidence gaps (Interview)

The left rail now shows five stages (Onboarding done, Interview current) plus a **Dashboard** link. On the fully-answered project, the interview shows:

```
Copilot: All interview gaps are covered. Generate architecture options next —
the package (including diagrams) follows once you pick one.

[Architecture options →]
```

The Evidence & Coverage rail on the right (now visible on every later stage, not just here):

```
Overall            100
Scope              100
Story readiness    100
Reliability        100
Security & compliance  100
Delivery           100
Review interview →
```

AI assist status showed `FAILED` with `3 AI follow-ups` and "Chat unreachable — deterministic gaps only" during an earlier check where the configured provider was momentarily unavailable — a real example of the labeled-fallback behavior, not a hidden failure.

## 4. Compare options

Default view is the **Matrix**, not cards — criteria as rows, options as columns:

```
                        Event-Driven          Modular Monolith        Serverless
                        Microservices          [RECOMMENDED]           Function-Based
                        ● selected             ○                       ○
FIT SCORE               90                     80                      75
COST                     High                   Medium                  Low
OPS                      Medium                 Low                     Medium
STACK          java-21, spring-boot,   java-21, spring-boot,   java-21, azure-functions,
                kafka, aks, postgres,   aks, postgres, kafka,   kafka, postgres, entra-id
                entra-id                entra-id

[Open package]          [Select this]           [Select this]
```

`[Matrix] [Cards]` toggle switches to the full pros/cons/assumptions card view. Selecting shows: *"Selection saved. These options stay available — regenerate only if you want a fresh set."* with a **View package →** button.

## 5. Browse the architecture package

Package index runs 1–18 plus Citations, one artifact at a time (`?a=<id>`), e.g. `12 · ARCHITECTURE BACKLOG`. The high-level design (artifact 1) opens with:

> The project employs an event-driven microservices architecture using Java 21, Spring Boot, Kafka, AKS, Postgres, and Entra ID. The trade-off is complexity in managing microservices and ensuring data consistency, but it achieves high scalability and resilience for handling up to 2k claims per hour with stringent availability and performance requirements.

From **Diagrams** or **Advisor** (both reached via the Package artifact index / rail, not their own rail entries — they inherit the Package highlight), a **← Back to package** link at the top returns to the *exact* artifact you were on — real browser history, confirmed by navigating to artifact 12, jumping to Diagrams, and returning to find `?a=arch_backlog` intact rather than reset to artifact 1.

Diagrams rendered live: L1 Context, L2 Containers, L3 Components, Sequence, Data flow — all marked present (✓). L1 Context shows `Clients → Claims Intake & Automated Adjudication → Azure / Notification service`, with an `Identity provider` actor for OIDC/SAML auth.

## 6. Ground a question in Knowledge

**Knowledge** shows the project embedded under **Your library**: `Project decisions — Claims Intake & Automated Adjudication · 22 chunks · embedded`.

Question asked, verbatim:

> In the project Claims Intake & Automated Adjudication what design was considered in the project and why?

Real response:

```
VIA KNOWLEDGE LIBRARY   CONFIDENCE: 90%   RETRIEVAL: PARTIAL   PATTERN · NULL

ANSWER
The primary design consideration for Claims Intake & Automated Adjudication focused on
creating a microservices architecture that facilitates event-driven interactions. This
architecture allows for quick claim processing and validates claims efficiently using a
Kafka-based event system. The design aims to automate low-value claims while ensuring
human oversight for flagged cases, significantly reducing processing time.

TALKING POINTS
- Microservices architecture improves scalability.
- Event-driven design reduces processing time for claims.
- Integration with existing systems is a key constraint.
- Service granularity must be balanced for performance.
- Automation of claims to reduce manual workload.
- Flexibility to adapt future changes in claim processing.

SOURCES
- Claims Intake & Automated Adjudication — High-level design (PROJECT)
- Architecture decisions — Claims Intake & Automated Adjudication (PROJECT)
- Design constraints (PROJECT)
- ADR-005: Event schema design for claims and policy interactions (PROJECT)
```

Every source is a real project artifact — not generic seed content, and not presented as bare model knowledge.

## 7. Export

`Download` on the default selection produced a real run:

```
Export ready
30 files · 5 ADRs · 5 diagrams

README.md
overview/architecture-overview.md
requirements/requirements.md
options/comparison.md
governance/standards-mapping.md
delivery/roadmap.md
delivery/migration-plan.md
ops/operational-readiness.md
cost/cost-model.md
review/architecture-review.md
traceability/matrix.md
hld/architecture.md
diagrams/c4-context.mmd
diagrams/c4-container.mmd
diagrams/sequence.mmd
diagrams/c4-component.mmd
diagrams/data-flow.mmd
backlog/implementation.md
backlog/epics-and-stories.md
threats/stride-lite.md
score/architecture-quality.md
decisions/ADR-001-go-with-event-driven-microservices-architecture.md
decisions/ADR-002-kafka-or-kafka-protocol-for-the-async-path.md
decisions/ADR-003-run-services-on-aks-kubernetes.md
decisions/ADR-004-level-of-decoupling-and-granularity-between-micr.md
decisions/ADR-005-event-schema-design-for-claims-and-policy-intera.md
decisions/README.md
risks/register.md
risks/README.md
project.json
[Download zip]
```

Recording this run surfaced a real bug: the summary line initially read **"6 ADRs"** because the count included `decisions/README.md` alongside the five numbered ADR files. Fixed in `ExportClient.tsx` to match `decisions/ADR-` specifically; re-verified against this same export run, now correctly reads **5 ADRs**.
