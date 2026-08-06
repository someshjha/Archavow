# Domain model — MVP

What Archavow persists and derives today. Keep the model small; package payload
carries most architecture structure as JSON rather than first-class tables.

ORM source of truth: `apps/api/app/db/models.py`.
Catalog of package contents: [ARTIFACT_CATALOG.md](./ARTIFACT_CATALOG.md).

## Entity map

### Persisted (active product path)

```text
WorkspaceSettings          # ai_overrides (chat/embedding provider + models)

Project                    # intake fields + stack_tags
  ├── Requirement          # source=intake | interview:<code> | …
  ├── ClarificationQuestion
  ├── ArchitectureOption   # three alternatives; at most one selected
  │     └── (design JSON: approach, assumptions, constraints, key_decisions)
  ├── ArchitecturePackage  # snapshot for selected option
  └── ExportRun            # generated file tree (path + content)

KnowledgeDocument          # source_class: org | seed | project
  └── KnowledgeChunk       # text + optional embedding / pgvector
```

### Embedded on ArchitecturePackage (JSON / text columns)

Not separate tables in MVP:

| Field | Role |
|-------|------|
| `documents` | Catalog markdown (`overview`, `requirements`, `hld`, …) + diagram extras |
| `hld_markdown` | HLD body (also mirrored in `documents.hld` when built) |
| `mermaid*` | C4 context / container / sequence (+ legacy `mermaid_deploy` column, unused in MVP UI) |
| `adrs[]` | Architecture decisions |
| `risks[]` | Risk register |
| `threats[]` | STRIDE-lite |
| `backlog[]` | Architecture backlog (cross-cutting technical work) |
| `epics[]` | Delivery backlog (business epics, stories, enablers) |
| `quality_score` | Evidence checklist (coverage states) |
| `citations[]` | Knowledge chunk refs used at generate time |
| `provenance` | `workflow_version`, providers, `artifact_catalog`, `ai_assist` |
| `ai_summary` | Optional executive blurb |
| `retrieval_status` | Knowledge retrieval health at generate time |

### Derived (not stored)

| Concept | How |
|---------|-----|
| `ProjectLifecycle` | Computed from requirements, questions, options, package, exports (`lifecycle.py`) |
| Completeness scorecard | Gap analysis over intake + interview answers (`scorecard.py`) |
| `R-00N` ids | Positional over **intake** requirements only |
| `stated_requirements` | Intake-sourced requirement texts feeding epics |

Stages: `intake` → `interview` → `options` → `package` → `export`.

### Legacy tables (present, not product path)

`artifacts`, `review_runs`, `review_findings` remain in the schema from an earlier
paste-and-lint review flow. MVP does not expose them; architecture review of
record is the human sign-off stub in `documents.review_record`.

## Key relationships

```text
Project 1—* Requirement
Project 1—* ClarificationQuestion
Project 1—* ArchitectureOption          # typically 3; ≤1 selected
Project 1—* ArchitecturePackage         # tied to selected option_id
Project 1—* ExportRun

ArchitecturePackage.option_id → ArchitectureOption

KnowledgeDocument 1—* KnowledgeChunk    # workspace-scoped (not project FK)

WorkspaceSettings                       # singleton row (id=1)
```

Constraints, assumptions, and stakeholders are **fields on intake / option
design JSON**, not separate entities.

## Requirement sources

| `source` | Meaning |
|----------|---------|
| `intake` | Stated at onboarding — drives `R-00N` and delivery backlog |
| `interview:<code>` | Answer to a clarification question — evidence only; unique per project+code |
| other | Reserved / future |

Interview answers never consume `R` numbers. Delivery stories cite intake refs only.

## Clarification questions

- Unique `(project_id, code)`
- `status`: `open` | `answered` | `skipped`
- Canonical codes and category floors live in `scorecard.py` (scope, story readiness, reliability, security, platform)
- Options unlock only when every category meets its floor (`completeness.ready`)

## Architecture options

- `origin`: `template` | `ai`
- `selected`: at most one true per project (partial unique index)
- `design`: structured approach metadata for advisor / package builders
- Human selection is required before package generation

## Delivery backlog shape (`epics[]`)

```text
Epic
  id: E-00N
  stories[] | enablers[]
    id: US-00N | EN-00N
    origin: evidence_derived | baseline_recommendation
    requirement_ref?: R-00N     # business stories only
    acceptance_criteria[]       # Given / When / Then (+ NFR checks)
```

`baseline_recommendation` items are platform defaults, not pretended intake evidence.

## Evidence checklist (`quality_score`)

Coverage per category: `missing` → `partial` → `evidenced` → `verified`.

- Overall = weakest category
- Keyword presence alone never reaches `verified`; interview floors can
- Also: `missing_evidence[]`, `blockers[]`, `method`, `confidence`, `label: evidence_checklist`
- Decision support only — not a certification score

## Traceability (MVP)

| From | To |
|------|----|
| Intake requirement `R-00N` | Delivery story (`requirement_ref`) |
| Selected option | Package (`option_id`) + diagrams / HLD / ADRs |
| ADR / document section | `citations[]` → knowledge chunks |
| Package | ExportRun files + README catalog numbers |

Full requirement → control → implementation chain remains a light draft
(`documents.traceability`), not a separate graph.

## Provenance (package)

Typical `provenance` payload includes:

- `workflow_version` (`package.v8`)
- `artifact_catalog` (`mvp.v2`)
- provider / model ids used
- `ai_assist` status map for generation steps
- retrieval / citation context as recorded at generate time

Generation is synchronous in-request (no Job / SSE entity in MVP).

## Deferred

Organization, Team, Policy engine, Exception workflow, Approval BPM,
first-class `DeploymentNode` / `Component` tables, `ProjectVersion` snapshots,
and multi-tenant User auth beyond optional `ARCHAVOW_API_KEY`.
