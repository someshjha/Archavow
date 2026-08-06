# Archavow local stack

.PHONY: up down logs test-api test-api-postgres test-web web-dev psql

up:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

logs:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f api web

# Default: in-memory SQLite (no Postgres required)
test-api:
	cd apps/api && pip install -e ".[dev]" && pytest -q

# Opt-in: real Postgres + Alembic + pgvector
test-api-postgres:
	cd apps/api && pip install -e ".[dev]" && \
	ARCHAVOW_TEST_DB=postgres pytest -q

test-web:
	cd apps/web && npm install && npm test

web-dev:
	cd apps/web && npm install && ARCHAVOW_API_URL=http://127.0.0.1:8000 npm run dev

psql:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml exec postgres \
		psql -U archavow -d archavow
