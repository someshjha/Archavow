# Archavow

**Turn incomplete requirements into an evidence-backed architecture package—before implementation begins.**

Archavow is a local-first architecture workbench for capturing requirements, closing evidence gaps, comparing viable designs, recording a human decision, and exporting the result as reviewable Markdown, Mermaid, and JSON.

> Understand → Design → Decide → Export

[![Archavow final walkthrough](docs/demo/archavow-demo.gif)](docs/demo/archavow-demo.gif)

[Open the final walkthrough](docs/demo/archavow-demo.gif) · [Run the guided demo](docs/DEMO.md) · [Read the transcript](docs/demo/TRANSCRIPT.md)

## Why Archavow

Architecture documents often look complete while hiding assumptions, missing requirements, and untraceable AI output. Archavow makes those boundaries visible:

- Human-entered requirements become stable `R-001…` references.
- Suggested answers are prompts, not invented facts, and cannot be accepted unchanged.
- AI output is schema-validated; deterministic fallbacks are clearly labeled.
- Knowledge responses distinguish grounded evidence from unverified model output.
- Generated stories, decisions, risks, and diagrams retain provenance.
- A human must select an architecture option before package generation.
- Evidence coverage is reported as `missing`, `partial`, `evidenced`, or `verified`—not as a certification score.

## Workflow

```mermaid
flowchart LR
    A["1. Intake<br/>objective, constraints, requirements"] --> B["2. Interview<br/>close evidence gaps"]
    B --> C["3. Options<br/>compare three alternatives"]
    C --> D{"Human selection"}
    D --> E["4. Package<br/>HLD, diagrams, ADRs, risks"]
    E --> F["5. Delivery backlog<br/>epics, stories, acceptance criteria"]
    E --> G["6. Export<br/>Git-ready ZIP"]

    K["Organization and project standards"] --> B
    K --> C
    K --> E
    AI["Ollama or OpenAI<br/>optional"] -. "bounded assist" .-> B
    AI -. "bounded assist" .-> C
    AI -. "bounded assist" .-> E
```

## System architecture

Archavow is intentionally a modular monolith: one Next.js application, one FastAPI service, and PostgreSQL with pgvector. This keeps local operation simple while preserving clear module boundaries.

```mermaid
flowchart TB
    U["Architect<br/>Browser"] --> WEB["Next.js 15 / React 19<br/>UI + server-side API proxy"]
    WEB --> API["FastAPI<br/>modular monolith"]

    subgraph CORE["Architecture workflow"]
      PROJECTS["Projects and lifecycle"]
      REQS["Requirements, gaps, scorecard"]
      OPTIONS["Options and human selection"]
      PACKAGE["Package, diagrams, ADRs,<br/>risks, threats, backlog"]
      KNOWLEDGE["Knowledge retrieval<br/>and grounding"]
      EXPORT["ZIP export"]
    end

    API --> PROJECTS
    PROJECTS --> REQS --> OPTIONS --> PACKAGE --> EXPORT
    REQS --> KNOWLEDGE
    OPTIONS --> KNOWLEDGE
    PACKAGE --> KNOWLEDGE

    API --> DB[("PostgreSQL 16<br/>pgvector")]
    EXPORT --> FILES[("Local data/<br/>downloadable exports")]

    API --> GATEWAY["Validated AI gateway"]
    GATEWAY --> CHAT{"Chat provider"}
    GATEWAY --> EMBED{"Embedding provider"}
    CHAT --> OLLAMA["Ollama"]
    CHAT --> OPENAI["OpenAI"]
    EMBED --> OLLAMA
    EMBED --> OPENAI
    EMBED --> NONE["Disabled<br/>keyword retrieval remains"]

    KNOWLEDGE --> DB
    GATEWAY -. "provider failure" .-> FALLBACK["Labeled deterministic fallback"]
    FALLBACK --> REQS
    FALLBACK --> OPTIONS
    FALLBACK --> PACKAGE
```

See [System Architecture](docs/SYSTEM_ARCHITECTURE.md) for module responsibilities, trust boundaries, and runtime details.

## What it produces

After an architect selects an option, Archavow creates:

- High-level architecture document
- C4 context and container diagrams
- Sequence and labeled data-flow diagrams
- Architecture Decision Records
- Risk register and STRIDE-lite threat model
- Evidence coverage checklist and blockers
- Implementation backlog
- Epics and user stories with Given/When/Then acceptance criteria
- Requirement citations and generation provenance

Exports are Git-ready:

```text
README.md
hld/architecture.md
diagrams/c4-context.mmd
diagrams/c4-container.mmd
diagrams/sequence.mmd
diagrams/data-flow.mmd
decisions/ADR-*.md
risks/register.md
backlog/implementation.md
backlog/epics-and-stories.md
threats/stride-lite.md
score/architecture-quality.md
citations.md
project.json
```

Business stories trace to intake requirements. Cross-cutting technical enablers are separated and labeled as baseline recommendations rather than evidence-derived work.

## Quick start

### Requirements

- Docker with Compose
- Git
- [Ollama](https://ollama.com) — required for the default configuration (chat via a local model). Install with `brew install ollama` (macOS) or `curl -fsSL https://ollama.com/install.sh | sh` (Linux). `make up` starts the server and pulls the default model (`llama3.2`) automatically if it isn't already there — set `AI_CHAT_PROVIDER=openai` in `.env` instead if you'd rather use OpenAI and skip installing Ollama.

```bash
git clone https://github.com/someshjha/Archavow.git
cd Archavow
cp .env.example .env
make up
```

Open:

- Application: [http://127.0.0.1:3001](http://127.0.0.1:3001)
- API health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- API documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

The default configuration uses Ollama for chat and disables embeddings. `make up` checks that Ollama is installed and running and pulls `llama3.2` before starting the stack — see Requirements above. If a chat request still fails at runtime for some other reason (model removed after startup, server killed mid-session, etc.), the core workflow continues with labeled deterministic fallbacks rather than blocking.

```bash
make logs       # follow API and web logs
make down       # stop without deleting database data
```

To remove the local PostgreSQL volume intentionally:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

This permanently deletes local project data.

## Run the demo

Start the stack, open the application, then follow [docs/DEMO.md](docs/DEMO.md):

```bash
make up
open http://127.0.0.1:3001
```

The included claims-adjudication scenario demonstrates:

1. Evidence-based onboarding and stable requirement references
2. Focused interview questions and coverage states
3. Three architecture alternatives and a human decision
4. Grounded package generation with Mermaid diagrams
5. Traceable epics, stories, and technical enablers
6. Git-ready export

## AI and knowledge configuration

Chat and embedding providers are configured independently.

| Capability | Options |
|---|---|
| Chat | Ollama, OpenAI |
| Embeddings | Ollama, OpenAI, disabled |
| Retrieval without embeddings | PostgreSQL keyword search |
| Retrieval with embeddings | PostgreSQL + pgvector |

Example Ollama configuration:

```dotenv
AI_CHAT_PROVIDER=ollama
AI_EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
ALLOW_PRIVATE_AI_URLS=true
OLLAMA_CHAT_MODEL=llama3.2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

`make up` only pulls the default chat model (`llama3.2`) automatically. If you turn on Ollama embeddings (`AI_EMBEDDING_PROVIDER=ollama`), pull the embedding model yourself first: `ollama pull nomic-embed-text`.

Example OpenAI configuration:

```dotenv
AI_CHAT_PROVIDER=openai
AI_EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=768
```

OpenAI credentials stay in the API environment. Saved workspace settings can override supported provider and model fields. Provider probes are available under **Settings**.

## Optional local API authentication

For a shared local environment:

```dotenv
ARCHAVOW_API_KEY=replace-with-a-long-random-value
```

All `/api/v1` routes then require a Bearer token. The browser unlock flow stores an HTTP-only session; direct clients must send the token themselves. `/health` remains public.

This is a single-key local safeguard, not enterprise identity or multi-tenant authorization.

## Development

### API

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export DATABASE_URL=postgresql+psycopg://archavow:archavow@127.0.0.1:5433/archavow
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Web

```bash
cd apps/web
npm install
ARCHAVOW_API_URL=http://127.0.0.1:8000 npm run dev
```

## Validation

Quality is guarded by a **deterministic evaluation harness** (pytest + Vitest), not a separate LLM golden-eval service. It encodes anti-slop contracts: evidence boundaries, schema validation, provenance labels, catalog order, grounding flags, and labeled AI fallbacks. Full map: [docs/EVAL_HARNESS.md](docs/EVAL_HARNESS.md).

```bash
make test-api             # SQLite unit/API suite (~270+ cases)
make test-api-postgres    # Alembic + PostgreSQL + pgvector + locking
make test-web             # Vitest (grounding UI, interview/options, BFF proxy)

cd apps/web
npx tsc --noEmit          # TypeScript validation (CI)
npm run build             # production build
```

GitHub Actions runs three independent jobs on `main` and PRs: SQLite API, PostgreSQL + pgvector API, and web typecheck + Vitest.

Headline golden cases include: package blocked until option select; interview floors before options; verbatim suggestion templates rejected; intake-only `R-00N` on delivery stories; evidence checklist coverage states (never 0–100); baseline enablers labeled; catalog-ordered export README; diagram honesty; strict JSON schema normalization; `grounded` true/false on knowledge ask.

## Repository

```text
Archavow/
├── apps/api/             # FastAPI, SQLAlchemy, Alembic, tests
├── apps/web/             # Next.js, React, Vitest
├── docs/                 # Maintained product and engineering guides
├── knowledge/            # Seed standards and architecture patterns
├── packages/             # Shared prompts, validators, patterns, UI tokens
├── data/                 # Local runtime/export storage
├── docker-compose.yml
└── Makefile
```

## Documentation

- [System architecture](docs/SYSTEM_ARCHITECTURE.md)
- [Guided demo](docs/DEMO.md)
- [AI workflows](docs/AI_WORKFLOWS.md)
- [Artifact catalog](docs/ARTIFACT_CATALOG.md)
- [Domain model](docs/DOMAIN_MODEL.md)
- [Evaluation harness](docs/EVAL_HARNESS.md) — golden cases, coverage map, CI
- [Test strategy](docs/TDD.md)

## Scope

Archavow currently targets local, single-organization architecture work. It does not provide enterprise SSO, multi-tenant administration, real-time collaborative editing, autonomous approval, repository bots, or automated cloud deployment.

AI assists the architect; it does not own the decision. Humans remain responsible for validating evidence, selecting an option, accepting decisions, and approving implementation.
