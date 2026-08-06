# Archavow web

Next.js 15 and React 19 interface for the evidence-to-export architecture workflow.

## Run locally

With the API available at `127.0.0.1:8000`:

```bash
cd apps/web
npm install
ARCHAVOW_API_URL=http://127.0.0.1:8000 npm run dev
```

Open [http://127.0.0.1:3001](http://127.0.0.1:3001).

## Validate

```bash
npm test
npm run lint
npm run build
```

Vitest covers server actions, API proxy behavior, knowledge grounding, interview/options interaction, package indexing, delivery backlog provenance, and artifact utilities.

For the full workflow, see the [root README](../../README.md) and [guided demo](../../docs/DEMO.md).
