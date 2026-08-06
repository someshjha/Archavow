# Evaluation harness

Archavow does **not** ship a separate LLM golden-eval service. Quality is guarded by
deterministic pytest + Vitest regressions that encode anti-slop contracts: evidence
boundaries, schema validation, provenance labels, catalog order, and fallback
behavior.

This document is the map of that harness — what it covers, how to run it, and
what each golden case is asserting.

Related: [TDD.md](./TDD.md) (engineering rules), [AI_WORKFLOWS.md](./AI_WORKFLOWS.md),
[ARTIFACT_CATALOG.md](./ARTIFACT_CATALOG.md).

## Philosophy

| Principle | Practice |
|-----------|----------|
| Prefer contracts over prose | Assert paths, coverage states, IDs, origins, HTTP codes — not LLM wording |
| Fake the network | `tests/fakes.py` providers; no live Ollama/OpenAI in CI |
| Fail closed on bad AI | Malformed JSON / schema misses → labeled templates or `AiAssistStatus.failed`, never silent invent |
| Evidence ≠ suggestion | Verbatim suggestion templates rejected; interview answers ≠ intake `R-00N` |
| Coverage ≠ certification | Evidence checklist uses `missing`/`partial`/`evidenced`/`verified` — never 0–100 |
| Catalog is law | Export README and package browser follow `mvp.v2` numbering |

LLM golden evals (rubrics over model prose) remain deferred. Until then, every
assist path must degrade to a tested deterministic fallback.

## How to run

```bash
# API — in-memory SQLite (default; no Postgres required)
make test-api
# or
cd apps/api && pip install -e ".[dev]" && pytest -q

# API — real Postgres + Alembic + pgvector + row locking
make test-api-postgres
# or
cd apps/api && ARCHAVOW_TEST_DB=postgres \
  DATABASE_URL=postgresql+psycopg://archavow:archavow@127.0.0.1:5433/archavow \
  pytest -q

# Web — Vitest
make test-web
# or
cd apps/web && npm test

# Typecheck (CI also runs this)
cd apps/web && npx tsc --noEmit
```

### CI (GitHub Actions)

Three independent jobs on `main` and PRs (`.github/workflows/ci.yml`):

1. **api** — SQLite pytest
2. **api-postgres** — `pgvector/pgvector:pg16` service + `ARCHAVOW_TEST_DB=postgres`
3. **web** — `npm ci` → `tsc --noEmit` → `npm test`

### Fixtures

- `TestClient` + per-test DB (`conftest.py`); Postgres when `ARCHAVOW_TEST_DB=postgres`
- `FakeChatProvider` / `FakeEmbeddingProvider` — no network
- Env defaults: chat `ollama`, embeddings `none` (keyword retrieval still works)

Scale today: ~47 API test modules / ~270+ cases; ~5 web Vitest suites.

---

## Coverage map

### AI gateway and providers

| File | What it locks |
|------|----------------|
| `test_ai_gateway.py` | Sole entry point; empty JSON → error; embed disabled → error |
| `test_null_embed.py` | `embedding_provider=none` path |
| `test_ai_registry.py` | Provider ids, dimensions (768) |
| `test_ai_config.py` | Env vs workspace overrides; no API key injection; mixed chat/embed; HLD fallback chain |
| `test_ai_schemas.py` | Shared AI schema shapes |
| `test_ai_fallback.py` | Expected provider failures degrade |
| `test_strict_json_schema.py` | Wire adapt (`additionalProperties`, required+nullable); normalize nulls out; reject invalid instances; open maps → `json_object`; options schema strict-ready |
| `test_ai_options_strict.py` | Fail closed on padded/fabricated/missing option fields |
| `test_options_ai.py` | AI options when chat OK; template fallback when chat fails; unexpected bugs do **not** become successful templates |
| `test_chat_assist.py` | Interview assist status paths |
| `test_hld_ai.py` | AI HLD when good; quality floor → deterministic fallback; chain entries |
| `test_url_safety.py` | Private URL allowlisting for AI endpoints |
| `test_settings_ai_api.py` | Settings probe / PATCH; secrets stay server-side |

### Interview, gaps, scorecard

| File | What it locks |
|------|----------------|
| `test_requirements_s1.py` | Intake requirements API |
| `test_gaps_unit.py` | Gap codes, neutral stubs, placeholder answers don't close, **verbatim suggestion templates rejected** |
| `test_completeness_scorecard.py` | Five categories, floors, overall alone never unlocks options, next question from weakest bucket, answer projection |
| `test_interview_gate_api.py` | Analyze payload, options locked until every floor met, answer-box preview matches score |
| `test_story_gaps_unit.py` | Story-readiness gaps; intake closes them, interview-derived rows do not; vague vs concrete answers |

### Options, package, catalog

| File | What it locks |
|------|----------------|
| `test_options_s2.py` / `test_options_unit.py` | Generate / select / package gate (409 until select) |
| `test_mvp_package_score.py` | Package has evidence checklist (coverage keys, **no numeric `score`**), backlog, threats; export paths; dashboard surfaces checklist |
| `test_package_documents.py` | MVP mandatory `documents.*` keys |
| `test_package_diagrams.py` / `test_diagrams_unit.py` / `test_package_c4_container.py` | Mermaid presence and export files |
| `test_package_adrs_risks.py` / `test_adrs_risks_unit.py` | ADR/risk structure; cloud-correct naming (EKS vs AKS) |
| `test_package_citations.py` | Citations when standards uploaded; empty when none |
| `test_package_query_bound.py` | Package generate query/locking bounds |
| `test_export_s5.py` | Export create / list / get / download |
| `test_export_readme_order.py` | README contents numbers ascend in catalog order; optional absences don't scramble order |
| `test_project_lifecycle.py` | Stage derivation intake→export + continue paths |
| `test_projects_api.py` | Project CRUD |

### Delivery backlog (epics)

| File | What it locks |
|------|----------------|
| `test_epics_unit.py` | Themed epics; every business story → `R-00N`; enablers `origin=baseline_recommendation`; no implementation language in customer stories; contiguous `E`/`US`/`EN` series from 1; **interview answers never become stories**; grammar (a/an, acronym case) |
| `test_delivery_backlog_api.py` | API surfaces epics on packaged projects |

### Evidence checklist and domain neutrality

| File | What it locks |
|------|----------------|
| `test_evidence_and_domain.py` | Risks/threats stay domain-neutral without payment evidence; seed citations don't inflate governance; keyword alone never `verified`; interview floors can; negated/bare RTO stays low; option cost/ops bands don't buy coverage; stack without intake context → alignment gaps |

### Anti-slop rounds (diagrams / HLD / assist)

| File | What it locks |
|------|----------------|
| `test_slop_round2.py` | Threats omit cloud-native assets without evidence; HLD assumptions not invented components |
| `test_slop_round3.py` | No invented event-driven stack; batch sequences without fake interactive roundtrips; Kafka only when evidenced; `as_ai_failure` degrades provider errors but re-raises bugs; consistency gap stack-neutral |

### Knowledge

| File | What it locks |
|------|----------------|
| `test_knowledge_s3.py` | Upload, list, keyword search with embeddings none |
| `test_knowledge_seed.py` | Idempotent seed; seed hidden from default list; **grounded=true** with KB hits; **grounded=false** + empty citations on model/web fallback; package can capture project decisions |
| `test_knowledge_ask_scoring.py` / `test_knowledge_scoring_unit.py` | Scored compose; Mermaid fence cleaning |
| `test_chunking_unit.py` | Chunk boundaries |

### Postgres-specific

| File | What it locks |
|------|----------------|
| `test_postgres_integration.py` | Alembic + pgvector paths when Postgres mode on |
| `test_postgres_persistence.py` | Persistence / locking behaviors |

### Health

| File | What it locks |
|------|----------------|
| `test_health.py` | `/health` public contract |

### Web (Vitest)

| File | What it locks |
|------|----------------|
| `KnowledgeClient.test.tsx` | Ungrounded warning for model fallbacks |
| `InterviewClient.test.tsx` | Error / assist failure surfaces |
| `OptionsClient.test.tsx` | Options UI contracts (origin / selection) |
| `route.test.ts` | BFF `/api/backend/[...path]` proxy |
| `actions.test.ts` | Cache revalidation helpers |

---

## Golden cases (deterministic v0)

These are the headline regressions — the cases a change must not break.

| # | Case | Assertion |
|---|------|-----------|
| 1 | Options gate | Package generate returns **409** until an option is selected |
| 2 | Interview floors | Options stay locked until every scorecard category meets its floor |
| 3 | Suggestion templates | Verbatim AI/stub suggestion text cannot be submitted as evidence |
| 4 | Intake-only `R-00N` | Delivery stories cite intake requirements; interview answers do not become stories or take `R` ids |
| 5 | Evidence checklist | Categories expose `coverage` states; no 0–100 `score` field; overall is weakest category |
| 6 | Keyword ≠ verified | Intake keywords alone never reach `verified`; interview floors can |
| 7 | Baseline enablers | Technical enablers use `origin=baseline_recommendation`, separate from `evidence_derived` stories |
| 8 | Package.v8 / mvp.v2 | Score + backlog + threats + C4 + documents; provenance carries workflow/catalog versions |
| 9 | Catalog export order | Export `README.md` lists artifact numbers ascending; optional gaps don't reorder |
| 10 | Diagram honesty | Mermaid omits stacks/components not evidenced in intake/option |
| 11 | Strict JSON | Gateway returns schema-normalized JSON; optional nulls dropped; invalid payloads rejected |
| 12 | AI fail-closed | Provider/schema failure → labeled templates; programming errors do not masquerade as success |
| 13 | Knowledge grounding | KB hit → `grounded=true` + citations; model/web → `grounded=false`, citations cleared |
| 14 | Seed ≠ governance | Seed/industry citations do not inflate evidence-checklist governance coverage |
| 15 | Export tree | ZIP/folder includes backlog, epics, threats, evidence checklist, diagrams, citations |

---

## What is intentionally out of scope

- Automated scoring of free-form LLM prose quality
- Multi-agent / tool-use trajectory evals
- Live provider soak tests in CI
- Visual / screenshot regression of Mermaid renders
- Load / performance benchmarks

When LLM golden evals arrive, they should sit **beside** this harness — never replace
the deterministic contracts above.
