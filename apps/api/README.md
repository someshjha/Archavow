# Archavow API

FastAPI modular monolith for projects, requirements interviews, architecture options, package generation, grounded knowledge retrieval, and export.

## Run locally

From the repository root, start PostgreSQL:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres
```

Then:

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export DATABASE_URL=postgresql+psycopg://archavow:archavow@127.0.0.1:5433/archavow
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- OpenAPI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Test

```bash
pytest -q
ARCHAVOW_TEST_DB=postgres pytest -q
```

The default suite uses in-memory SQLite. PostgreSQL mode runs Alembic migrations and validates pgvector and locking behavior.

See [System Architecture](../../docs/SYSTEM_ARCHITECTURE.md), [AI Workflows](../../docs/AI_WORKFLOWS.md), and [TDD](../../docs/TDD.md).
