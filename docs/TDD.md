# Test strategy (TDD)

**Rule:** red → green → refactor. Prefer API contract tests under `apps/api/tests/`
before UI polish. Prefer asserting **contracts** (status codes, IDs, origins,
coverage states, file paths, schema shape) over free-form LLM prose.

The regression **map** and golden cases live in [EVAL_HARNESS.md](./EVAL_HARNESS.md).
This document is how we write and run tests day to day.

## How to run

```bash
# API — in-memory SQLite (default; no Postgres required)
make test-api
# or
cd apps/api && pip install -e ".[dev]" && pytest -q

# API — Postgres + Alembic + pgvector + locking
make test-api-postgres
# needs DATABASE_URL (compose publishes Postgres at 127.0.0.1:5433)
# ARCHAVOW_TEST_DB=postgres pytest -q

# Web — Vitest
make test-web
# or: cd apps/web && npm test

# Typecheck (also in CI)
cd apps/web && npx tsc --noEmit
```

CI (`.github/workflows/ci.yml`) runs three independent jobs: SQLite API,
Postgres API, web `tsc` + Vitest.

## Layers

| Layer | Location | Use for |
|-------|----------|---------|
| Unit | `apps/api/tests/test_*_unit.py`, builders | Pure builders (epics, diagrams, scorecard, gaps) |
| API contract | `apps/api/tests/test_*_api.py`, `test_*_s*.py` | HTTP status, gates, payloads via `TestClient` |
| Gateway / schema | `test_ai_*`, `test_strict_json_schema.py` | Provider fakes, normalize/validate, fail-closed |
| Anti-slop | `test_evidence_*`, `test_slop_*`, `test_epics_*` | Evidence honesty, origins, no invented stack |
| Postgres | `test_postgres_*.py` (when `ARCHAVOW_TEST_DB=postgres`) | Migrations, pgvector, row locks |
| Web | `apps/web/**/*.test.ts(x)` | Grounding UI, options/interview errors, BFF proxy |

Order of preference when adding behavior:

1. Unit or API test that fails for the bug/contract  
2. Implementation  
3. Web test only if the UI has distinct provenance/error presentation  

## Fixtures and doubles

- `conftest.py` — per-test DB + `TestClient`; chat `ollama` / embeddings `none` by default  
- `fakes.py` — `FakeChatProvider` / `FakeEmbeddingProvider` (no network)  
- Never call live Ollama/OpenAI in CI  
- Assert export **paths and evidence strings**, not generated narrative quality  

## Non-negotiables

### AI boundary

1. Feature modules call **`AIGateway` only** — never Ollama/OpenAI SDKs.  
2. Chat and embeddings are independent settings.  
3. `OPENAI_API_KEY` never appears in Settings GET/PATCH bodies or DB.  
4. Empty JSON from chat → `EmptyAIResponseError`.  
5. Embed with `embedding_provider=none` → `EmbeddingDisabledError`.  
6. Embedding vectors must match `embedding_dimensions` (default **768**).  
7. Expected provider failures → labeled fallback / `AiAssistStatus.failed`; unexpected bugs **re-raise** (do not become successful templates).  
8. Gateway returns **schema-normalized** JSON (optional nulls dropped); invalid instances rejected against the original schema.

### Evidence and product contracts

9. Evidence checklist uses coverage states (`missing` / `partial` / `evidenced` / `verified`) — never invent a 0–100 certification score.  
10. Keyword presence alone never reaches `verified`; interview floors can.  
11. Intake requirements own `R-00N`; interview answers do not become delivery stories.  
12. Verbatim suggestion-template submits are rejected.  
13. Technical enablers use `origin=baseline_recommendation`; business stories use `evidence_derived`.  
14. Package / export follow catalog order (`mvp.v2`); provenance carries `package.v8`.  
15. Knowledge ask: KB hit → `grounded=true` + citations; model/web → `grounded=false`, citations cleared.  
16. Package generate returns **409** until an option is selected; options stay locked until scorecard floors are met.

## What “done” means for a change

- New assist path: fake-provider success **and** failure/fallback tests  
- New package field or export path: unit + export path/README order if numbered  
- New interview code: scorecard category membership + gate behavior  
- UI provenance/warning: Vitest asserting the visible label  

Do not merge with only a manual demo when a deterministic assertion is possible.

## Out of scope for this suite

- Scoring free-form LLM prose quality  
- Live provider soak tests  
- Mermaid visual screenshot diffs  
- Load / performance benchmarks  

Those may arrive later **beside** this harness — see [EVAL_HARNESS.md](./EVAL_HARNESS.md).

## Current product under test

**MVP (`package.v8`, `artifact_catalog: mvp.v2`):** interview scorecard gate, three options + human select, package documents/diagrams/ADRs/risks/threats/backlogs, evidence checklist, knowledge grounding, Git-ready export.
