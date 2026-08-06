# AI workflows

**Rule:** controlled pipelines with specialized steps — not one giant prompt and not a swarm of autonomous agents.

Logical roles (Requirement Analyst, Solution Architect, …) are **prompted steps** inside modules. They are not separate runtime agents.

Every AI call site goes through `AIGateway`. Provider SDKs are never used from feature modules.

## 1. Requirements interview

```text
1. Load intake (objective, problem, constraints, scale, cloud, …)
2. Deterministic gap analysis (structural codes + completeness scorecard)
3. Neutral stub prompts: "Clarify: {label}" when AI is unavailable
4. AI assist (when chat works):
   - Rewrite open gap prompts for THIS project's actors/workflows
   - Optionally add ai_* follow-ups (requirements / nfrs / security only)
   - May report sufficient=true to stop follow-ups
5. Architect answers ← human gate
6. Reject verbatim suggestion-template submits (prompt-shaped drafts only)
7. Answers become requirement evidence; scorecard unlocks options when floors are met
```

Interview succeeds when coverage floors are met and the problem is clear enough to propose distinct approaches — not when every checklist code is merely present.

Assist status is `ok` | `skipped` | `failed`. Expected provider failures degrade; unexpected programming errors propagate.

## 2. Architecture options

```text
1. Build ProjectContext from intake + answered interview evidence
2. AI: exactly 3 DISTINCT solution approaches (structured JSON)
   Fields: approach, assumptions, constraints, key_decisions,
   pros/cons, stack, cost/ops bands, fit_score, recommended
3. Validate against OPTIONS_SCHEMA via AIGateway (see §7)
4. On provider/schema failure: deterministic templates
   (modular services / monolith / multi-site), origin=template
5. Persist three options; UI shows AI vs template provenance
6. User selects one option ← human gate (required before package)
```

Generation locks the project row. Existing options are not deleted until a full replacement set of three is ready. Unexpected bugs are not turned into a successful template response.

## 3. Architecture package

After selection, package builders assemble the artifact catalog ([ARTIFACT_CATALOG.md](./ARTIFACT_CATALOG.md)):

```text
1. Retrieve knowledge citations (org / project; seed labeled industry)
2. Optional AI executive summary (falls back if chat fails)
3. HLD: AI structured sections when available; deterministic markdown otherwise
4. Mermaid: context, container, sequence, data-flow (deterministic builders)
5. ADRs, risks, STRIDE-lite threats from context + selected option
6. Architecture backlog + delivery epics/stories
   - Business stories cite requirement refs
   - Technical enablers tagged origin=baseline_recommendation
7. Evidence checklist: coverage states missing → partial → evidenced → verified
   (keyword method; interview floors can verify; never a fake 0–100 certification)
8. Persist package + provenance workflow_version=package.v8,
   artifact_catalog=mvp.v2
9. Optional capture of decision notes into project knowledge
```

Diagrams follow C4-style hierarchy with nested boundaries and labeled flows. Package browsing is one artifact at a time in the web UI.

## 4. Knowledge ask

```text
1. Keyword (and semantic, if embeddings enabled) retrieval
2. If KB candidates score well: compose grounded answer + citations
3. If KB is thin/weak: model or optional web fallback
4. grounded=false for model/web; citations cleared (no inherited KB provenance)
5. UI shows an explicit ungrounded warning when grounded is false
```

`retrieval_status` is `ok` | `partial` | `degraded` | `failed`. Embeddings may be `none`; keyword search still works.

## 5. Advisor / ADR assist

Advisor compares selected vs alternative options using stored design metadata. ADR drafts are part of package generation; accepting ADR status remains a human action.

## 6. Tooling policy

| Concern | Owner |
|---------|--------|
| JSON Schema contract | `jsonschema` Draft 2020-12 after provider wire adapt |
| Mermaid / package structure | Deterministic builders + tests |
| Reasoning / wording | LLM (advisory) |
| Architecture of record | Human selection and edits |

## 7. AI gateway and structured output

| Concern | Rule |
|---------|------|
| Chat | `ollama` \| `openai` (Settings + env) |
| Embeddings | `ollama` \| `openai` \| `none` — independent of chat |
| Entry point | `AIGateway.complete_json` / `complete_text` / `embed` |
| Wire format | `to_strict_schema` for providers that support strict JSON Schema; open maps fall back to `json_object` |
| Optional fields | Become required + nullable on the wire; nulls normalized to omit before return |
| Contract check | `Draft202012Validator.check_schema` + validate instance; return normalized object |
| Failures | `AI_PROVIDER_ERRORS` → `AiAssistStatus(failed)`; other exceptions re-raise |
| Secrets | `OPENAI_API_KEY` server-side only |
| Vectors | Fixed **768** dims (`pgvector`); keyword path when embeddings disabled |
| Provenance | `workflow_version`, provider/model ids on generated packages |

Default: local Ollama. OpenAI optional. Same call-site schemas regardless of provider.

## 8. What is not in MVP

- Separate agent runtimes or multi-agent orchestration
- Versioned prompt pack under `packages/prompts/`
- Job/SSE progress streams for generation steps
- Autonomous approval or unattended option selection

Regression coverage is pytest + Vitest ([TDD.md](./TDD.md), [EVAL_HARNESS.md](./EVAL_HARNESS.md)), not a separate LLM golden-eval service.
