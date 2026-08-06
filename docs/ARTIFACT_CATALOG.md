# Architecture artifact catalog

What architects produce in Archavow, and what the package and export include today.

**Versions:** package provenance uses `workflow_version: package.v8` and `artifact_catalog: mvp.v2`.

## Catalog

| # | Artifact | MVP | Package source | Export path(s) | UI `?a=` |
|---|----------|-----|----------------|----------------|----------|
| 1 | Architecture overview | **mandatory** | `documents.overview` | `overview/architecture-overview.md` | `overview` |
| 2 | Requirements | **mandatory** | `documents.requirements` | `requirements/requirements.md` | `requirements` |
| 3 | Architecture options | **mandatory** | Options API + `documents.options_comparison` | `options/comparison.md` | `options` |
| 4 | Architecture diagrams | **mandatory** | `mermaid`, `mermaid_container`, `mermaid_sequence`, `documents.diagram_component`, `documents.diagram_dataflow` | `diagrams/c4-*.mmd`, `sequence.mmd`, `data-flow.mmd` | `diagrams` |
| 5 | High-level design | **mandatory** | `hld_markdown` / `documents.hld` (AI sections when available, else deterministic) | `hld/architecture.md` | `hld` |
| 6 | ADRs | **mandatory** | `adrs[]` | `decisions/` | `adrs` |
| 7 | Risk register | **mandatory** | `risks[]` | `risks/` | `risks` |
| 8 | Threat model | **mandatory** | STRIDE-lite `threats[]` | `threats/stride-lite.md` | `threats` |
| 9 | Evidence checklist | **mandatory** | `quality_score` | `score/architecture-quality.md` | `score` |
| 10 | Standards and compliance mapping | conditional | `documents.standards_mapping` | `governance/standards-mapping.md` | `standards` |
| 11 | Implementation roadmap | **mandatory** | `documents.roadmap` | `delivery/roadmap.md` | `roadmap` |
| 12 | Architecture backlog | **mandatory** | `backlog[]` | `backlog/implementation.md` | `arch_backlog` |
| 13 | Delivery backlog | **mandatory when intake requirements exist** | `epics[]` | `backlog/epics-and-stories.md` | `delivery_backlog` |
| 14 | Migration and deployment plan | **mandatory** | `documents.migration_plan` | `delivery/migration-plan.md` | `migration` |
| 15 | Operational readiness plan | **mandatory** | `documents.operational_readiness` | `ops/operational-readiness.md` | `ops` |
| 16 | Cost model | conditional | `documents.cost_model` | `cost/cost-model.md` | `cost` |
| 17 | Architecture review record | **mandatory** | `documents.review_record` (human sign-off stub) | `review/architecture-review.md` | `review` |
| 18 | Traceability matrix | conditional | `documents.traceability` | `traceability/matrix.md` | `traceability` |
| 19 | Exportable handoff package | **mandatory** | Export API | ZIP / folder + `README.md` (+ optional `project.json`, provenance block) | — |
| — | Citations | when present | `citations[]` | `citations.md` | `citations` |

## Package browser

The package page shows **one artifact at a time**. The index lists catalog order from `apps/web/lib/artifacts.ts`. Selecting an entry updates `?a=<id>` via `history.replaceState` (content pane only — no full navigation).

Missing optional sections appear unavailable in the index rather than as empty cards.

## Evidence checklist (artifact 9)

Not a 0–100 certification score. Payload shape:

- `overall`: weakest category coverage among `missing` | `partial` | `evidenced` | `verified`
- `categories[]`: `{ id, label, weight, coverage }`
- `missing_evidence[]`, `blockers[]`
- `label: evidence_checklist`, `method: intake_keyword_presence`, `confidence: low|medium`

Keyword presence alone never reaches `verified`; interview category floors can. Option stack is used only for alignment deductions, never free coverage from cost/ops bands.

## Delivery backlog (artifact 13)

- **Business epics / stories** — `origin: evidence_derived` when traced to intake requirements (`R-00N`)
- **Technical enablers** — `origin: baseline_recommendation` (platform defaults, not pretended evidence)
- Acceptance criteria use Given / When / Then; NFR checks attach where relevant
- UI shows **baseline** chips for `baseline_recommendation` items

ID series (no shared counters, no gaps): `R-001…` intake requirements, `E-001…` epics, `US-001…` business stories, `EN-001…` enablers, `AC-1…` per story. Interview answers do not consume `R` numbers.

## Diagrams (artifact 4)

MVP emits C4 **L1 context**, **L2 containers** (nested FE/BE/data), **L3 components** when built, plus **sequence** and a labeled **data-flow**. Deployment / region–VPC topology diagrams are out of scope. Relation labels carry protocols and numbered steps where useful. No dedicated cloud-vendor icon packs in Mermaid MVP.

## Conditional policy (10, 16, 18)

Emit light drafts on every package so larger projects can expand them without regenerating structure. Missing regulatory detail, numeric cost, or full req→control chains are explicit gaps — not silent omissions.

## Numbering history

Every artifact uses one whole number. `mvp.v1` used `12b` for delivery backlog; `mvp.v2` assigns it **13** and shifts later plans. **12** remains cross-cutting architecture work; **13** is delivery work traced to stated requirements.

## Regeneration

Selecting an option and generating the package refreshes all artifacts. Re-run after interview answers or knowledge citations change. Export reads the current package snapshot.
