# Archavow guided demo

This 10–15 minute golden path demonstrates the evidence-to-export workflow, plus grounded knowledge Q&A. It works without an LLM; AI-enhanced wording and generation are optional.

Catalog contract: [ARTIFACT_CATALOG.md](./ARTIFACT_CATALOG.md) (`package.v8`, `mvp.v2`). AI step boundaries: [AI_WORKFLOWS.md](./AI_WORKFLOWS.md).

[Watch the final walkthrough](demo/archavow-final-demo.mp4) · [Read its transcript](demo/TRANSCRIPT.md)

## Before the demo

```bash
cp .env.example .env
make up
curl http://127.0.0.1:8000/health
```

`make up` now checks Ollama (the default chat provider) is installed, starts it if needed, and pulls `llama3.2` before the stack comes up — see the README's Requirements section if it fails there.

Open [http://127.0.0.1:3001](http://127.0.0.1:3001).

Optional preparation:

- Open **Settings** and probe the configured chat provider. Note that Settings can override the provider at runtime independently of `.env` — `/health`'s `ai.chat_provider` is the source of truth for what's actually answering requests, not the `.env` default.
- Open **Knowledge** and load the seed library.
- Add one organizational Markdown standard to demonstrate preferred grounding.

Orient on the shell before starting: a left rail carries workspace navigation (Projects, Knowledge, Settings) and, once inside a project, the five-stage progress (Onboarding → Interview → Options → Package → Export) plus a **Dashboard** link back to the project overview. A right-hand **Evidence & Coverage** panel stays visible on every stage after Onboarding — not just the Interview page — so coverage is never more than a glance away.

## Scenario

The built-in scenario is **Claims Intake & Automated Adjudication**. It describes a manual email/PDF claims process and includes ten business requirements covering intake, validation, automated decisions, human review, payment, status, audit, and reporting.

The constraints use Azure, Java 21, Kafka, AKS, PostgreSQL, and Entra ID. These are scenario evidence—not defaults silently invented by Archavow.

## Walkthrough

### 1. Create the project

1. From **Projects**, select **+ Start onboarding**.
2. Select **Load demo scenario**.
3. Review the objective, problem, requirements, cloud, scale, and constraints.
4. Watch the requirements ledger: each line becomes a numbered `R-00N` entry the moment it's added, not after a bulk save. Confirm ten requirements are captured, traced as `R-001–R-010`.
5. Select **Save & start interview**.

Checkpoint: requirements have stable references before any architecture is generated.

### 2. Close evidence gaps

1. Review the interview coverage states — both inline (with the "before options unlock" checklist and AI-assist status) and in the persistent Evidence & Coverage rail on the right, which now follows you to every later stage too.
2. Answer the outstanding questions for current approach, integrations, team constraints, residency, authentication, and cloud topology.
3. Edit any suggested prompt in your own words; an unchanged prompt cannot become evidence.
4. Continue when material blockers are closed.

Checkpoint: coverage is `missing`, `partial`, `evidenced`, or `verified`. Decision support only—not certification.

### 3. Compare options

1. Open **Options**. The default view is a **comparison matrix** — criteria (fit score, cost, ops burden, stack) as rows, the three alternatives as columns, so trade-offs read across a line instead of jumping between cards. Toggle to **Cards** for the fuller pros/cons/assumptions view per option.
2. Inspect each option's origin. If AI is unavailable, alternatives are labeled as deterministic templates.
3. Select one option (click its column header in Matrix view, or its card in Cards view).

Checkpoint: package generation requires an explicit human decision.

### 4. Browse the architecture package

The package page shows **one artifact at a time** (`?a=<id>`). Use the index to walk catalog order 1–18 (plus Citations when present).

Call out at least:

| # | Artifact | What to show |
|---|----------|--------------|
| 4 | Diagrams | C4 L1–L3, sequence, labeled data-flow (no deploy/VPC topology) |
| 5 | HLD | Sections match the selected option's stack |
| 6–8 | ADRs, risks, threats | Structured fields; STRIDE-lite assets match evidence |
| 9 | Evidence checklist | Coverage states + gaps/blockers — **not** a 0–100 score |
| 12 | Architecture backlog | Cross-cutting technical work |
| 13 | Delivery backlog | Business stories with `R-00N`; enablers tagged **baseline** |
| — | Citations / provenance | Grounding labels; `package.v8` / `mvp.v2` in provenance |

From artifact 4 (Diagrams) or the Advisor page, note the **← Back to package** link at the top — it returns to the exact artifact you were on (real browser history), not the catalog default.

Checkpoint: ungrounded knowledge responses are visibly labeled. Package evidence favors project and organizational sources over generic seed content.

### 5. Inspect delivery traceability

Open artifact **13 · Delivery backlog** and expand several stories.

Confirm:

- Business stories include `R-00N` references (`origin: evidence_derived`).
- Acceptance criteria use Given / When / Then.
- Customer-facing stories describe outcomes, not implementation language.
- Technical enablers live under a `baseline_recommendation` epic and show **baseline** chips.
- Runtime, walking-skeleton, CI, observability, and authentication work is not misrepresented as a customer requirement.

### 6. Ground a question in Knowledge

Once a package exists, the project's own HLD, ADRs, and design constraints are embedded and searchable — not just uploaded org standards.

1. Open **Knowledge**. Confirm the project appears under **Your library** as `Project decisions — <project name>` with a chunk count.
2. Ask a project-specific question, e.g.:

   > In the project Claims Intake & Automated Adjudication what design was considered in the project and why?

3. Confirm the response shows `VIA KNOWLEDGE LIBRARY`, a confidence percentage, and a retrieval status (`partial`/`full`) — not a bare, unlabeled answer.
4. Expand **Sources** and confirm the citations point at real project artifacts (e.g. `Claims Intake & Automated Adjudication — High-level design`, a specific ADR) rather than generic seed content.

Checkpoint: an answer's grounding is always visible and traceable to a real source — never presented as bare model knowledge when project evidence exists.

### 7. Export

Open **Export**, keep the default artifact selection, and download the ZIP. Once the run completes, the summary line reads like a commit message (`N files · M ADRs · K diagrams`), computed from the actual file list the export produced — not a guess.

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

If Ollama itself isn't installed or running, `make up` now fails before any container starts, with the exact install command for your OS — a good, quick way to show the prerequisite check is real rather than a silent degradation.

## What a successful demo proves

- Intake facts remain distinguishable from prompts, AI output, and baseline recommendations.
- Requirements trace into the business backlog.
- Architecture options remain human-controlled.
- Coverage, grounding, and fallback status remain visible — on every stage, not just the one that produced them.
- Knowledge answers are traceable to a real source, or clearly labeled when they aren't.
- The final artifact package is coherent, portable, and reviewable.

## Presenter close

> Archavow does not automate architecture accountability. It creates a structured, evidence-backed decision record so architects can move faster without hiding uncertainty.
