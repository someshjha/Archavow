# Archavow local stack

.PHONY: up down ollama-up logs test-api test-api-postgres test-web web-dev psql

up:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Host-level Ollama preflight for the default AI_CHAT_PROVIDER=ollama config.
# Skips entirely if the project is configured for a different provider.
ollama-up:
	@provider=$$( [ -f .env ] && grep -m1 '^AI_CHAT_PROVIDER=' .env | cut -d= -f2- ); \
	provider=$${provider:-ollama}; \
	if [ "$$provider" != "ollama" ]; then \
		echo "AI_CHAT_PROVIDER=$$provider — skipping Ollama preflight."; \
		exit 0; \
	fi; \
	if ! command -v ollama >/dev/null 2>&1; then \
		echo "Ollama is required (AI_CHAT_PROVIDER=ollama) but isn't installed."; \
		echo "  macOS:  brew install ollama"; \
		echo "  Linux:  curl -fsSL https://ollama.com/install.sh | sh"; \
		echo "  Or set AI_CHAT_PROVIDER=openai in .env to use OpenAI instead."; \
		exit 1; \
	fi; \
	if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then \
		echo "Starting Ollama server..."; \
		nohup ollama serve >/tmp/archavow-ollama.log 2>&1 & \
		attempt=0; \
		until curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; do \
			attempt=$$((attempt + 1)); \
			if [ $$attempt -ge 15 ]; then \
				echo "Ollama server did not start within 15s. Check /tmp/archavow-ollama.log"; \
				exit 1; \
			fi; \
			sleep 1; \
		done; \
	fi; \
	model=$$( [ -f .env ] && grep -m1 '^OLLAMA_CHAT_MODEL=' .env | cut -d= -f2- ); \
	model=$${model:-llama3.2}; \
	echo "Pulling Ollama model: $$model (no-op if already present)"; \
	ollama pull "$$model"

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
