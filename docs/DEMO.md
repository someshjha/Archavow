# Archavow guided demo

This 10–15 minute golden path demonstrates the evidence-to-export workflow. It works without an LLM; AI-enhanced wording and generation are optional.

Catalog contract: [ARTIFACT_CATALOG.md](./ARTIFACT_CATALOG.md) (`package.v8`, `mvp.v2`). AI step boundaries: [AI_WORKFLOWS.md](./AI_WORKFLOWS.md).

[Open the final walkthrough](demo/archavow-demo.gif) · [Read its transcript](demo/TRANSCRIPT.md)

## Before the demo

```bash
cp .env.example .env
make up
curl http://127.0.0.1:8000/health
```

Open [http://127.0.0.1:3001](http://127.0.0.1:3001).

Optional preparation:

- Open **Settings** and probe the configured chat provider.
- Open **Knowledge** and load the seed library.
- Add one organizational Markdown standard to demonstrate preferred grounding.

## Scenario

The built-in scenario is **Claims Intake & Automated Adjudication**. It describes a manual email/PDF claims process and includes ten business requirements covering intake, validation, automated decisions, human review, payment, status, audit, and reporting.

The constraints use Azure, Java 21, Kafka, AKS, PostgreSQL, and Entra ID. These are scenario evidence—not defaults silently invented by Archavow.

## Walkthrough

### 1. Create the project

1. Select **New project**.
2. Select **Load demo scenario**.
3. Review the objective, problem, requirements, cloud, scale, and constraints.
4. Confirm that the UI reports ten captured requirements, traced as `R-001–R-010`.
5. Select **Save & start interview**.

Checkpoint: requirements have stable references before any architecture is generated.

### 2. Close evidence gaps

1. Review the interview coverage states.
2. Answer the outstanding questions for current approach, integrations, team constraints, residency, authentication, and cloud topology.
3. Edit any suggested prompt in your own words; an unchanged prompt cannot become evidence.
4. Continue when material blockers are closed.

Checkpoint: coverage is `missing`, `partial`, `evidenced`, or `verified`. Decision support only—not certification.

### 3. Compare options

1. Open **Options**.
2. Compare the three alternatives (trade-offs, cost band, operational burden, evidence alignment).
3. Inspect each option’s origin. If AI is unavailable, alternatives are labeled as deterministic templates.
4. Select one option.

Checkpoint: package generation requires an explicit human decision.

### 4. Browse the architecture package

The package page shows **one artifact at a time** (`?a=<id>`). Use the index to walk catalog order 1–18 (plus Citations when present).

Call out at least:

| # | Artifact | What to show |
|---|----------|--------------|
| 4 | Diagrams | C4 L1–L3, sequence, labeled data-flow (no deploy/VPC topology) |
| 5 | HLD | Sections match the selected option’s stack |
| 6–8 | ADRs, risks, threats | Structured fields; STRIDE-lite assets match evidence |
| 9 | Evidence checklist | Coverage states + gaps/blockers — **not** a 0–100 score |
| 12 | Architecture backlog | Cross-cutting technical work |
| 13 | Delivery backlog | Business stories with `R-00N`; enablers tagged **baseline** |
| — | Citations / provenance | Grounding labels; `package.v8` / `mvp.v2` in provenance |

Checkpoint: ungrounded knowledge responses are visibly labeled. Package evidence favors project and organizational sources over generic seed content.

### 5. Inspect delivery traceability

Open artifact **13 · Delivery backlog** and expand several stories.

Confirm:

- Business stories include `R-00N` references (`origin: evidence_derived`).
- Acceptance criteria use Given / When / Then.
- Customer-facing stories describe outcomes, not implementation language.
- Technical enablers live under a `baseline_recommendation` epic and show **baseline** chips.
- Runtime, walking-skeleton, CI, observability, and authentication work is not misrepresented as a customer requirement.

### 6. Export

Open **Export**, keep the default artifact selection, and download the ZIP.

Expected structure (catalog numbers appear in `README.md`):

```text
README.md
overview/architecture-overview.md
requirements/requirements.md
options/comparison.md
diagrams/c4-context.mmd
diagrams/c4-container.mmd
diagrams/sequence.mmd
diagrams/c4-component.mmd      # when generated
diagrams/data-flow.mmd
hld/architecture.md
decisions/
risks/
threats/stride-lite.md
score/architecture-quality.md
governance/standards-mapping.md
delivery/roadmap.md
backlog/implementation.md
backlog/epics-and-stories.md
delivery/migration-plan.md
ops/operational-readiness.md
cost/cost-model.md
review/architecture-review.md
traceability/matrix.md
citations.md
project.json
```

Checkpoint: the exported package can be reviewed in Git without running Archavow.

## Demonstrating fallback behavior

To show that the core workflow does not depend on a live model:

1. Set `AI_EMBEDDING_PROVIDER=none` (and/or stop the configured chat provider).
2. Generate interview guidance or options.
3. Confirm that fallback output is labeled and that keyword knowledge retrieval remains available.

Do not present deterministic templates as AI recommendations. Their origin is intentionally visible.

## What a successful demo proves

- Intake facts remain distinguishable from prompts, AI output, and baseline recommendations.
- Requirements trace into the business backlog.
- Architecture options remain human-controlled.
- Coverage, grounding, and fallback status remain visible.
- The final artifact package is coherent, portable, and reviewable.

## Presenter close

> Archavow does not automate architecture accountability. It creates a structured, evidence-backed decision record so architects can move faster without hiding uncertainty.
