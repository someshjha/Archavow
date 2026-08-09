# Roadmap

This is a working roadmap, not a commitment schedule. Items are grouped by
how soon they're likely to land — **Now** (in progress or next up), **Next**
(~6 months out), **Later** (bigger, less certain bets) — and every item
traces to something Archavow already says about itself: an explicit gap in
[README.md's Scope section](README.md#scope), a live evidence-coverage
state on the Dashboard, or a checkpoint already noted in
[docs/DEMO.md](docs/DEMO.md). Nothing here is speculative feature
brainstorming disconnected from the current product.

## Open question: local-first vs. team use

Archavow is [local-first](README.md#why-archavow) today — one Docker
Compose stack, one organization's local data. Several items below (shared
deploy mode, threaded review, a possible hosted tier) move toward
multi-user and collaborative use, which implies a shared backend. That
tension is **not resolved here**. Near-term items stay local-first-safe
regardless of how it's eventually decided.

## Now

### Evidence-gap remediation + pre-export completeness checkpoint

The Dashboard's evidence checklist scores ten categories (requirements
completeness, scalability, reliability, security, operability, data
architecture, integration design, maintainability, cost awareness,
governance compliance), but today only five of the ten are backed by an
actual interview question — the other seven can only ever reach
`evidenced`, never `verified`, and there's no guided way to close them.

- Every `missing`/`partial` category gets a **Close this gap →** action.
  Six categories reopen Interview with a new targeted question; Governance
  compliance opens Knowledge to cite an org standard instead, since that's
  what actually satisfies it.
- The six interview-backed categories gain a real interview cap, so they
  can reach `verified` for the first time.
- Before Export runs, a completeness checkpoint lists any categories still
  `missing`/`partial` and why, with two explicit choices: close the gaps
  now, or export anyway. This is advisory, not a hard block — consistent
  with evidence coverage already being reported as a checklist, not a
  certification score.
- Closing a gap after Package/Export already exist doesn't silently
  regenerate anything — affected artifacts are flagged "evidence changed
  since generation" with an explicit Recreate package action.

### Deployment/infra topology diagram

The diagram set (C4 context/container/component, sequence, data-flow) does
not yet include a deployment/VPC topology view — already noted as a gap in
the guided demo walkthrough. Add it as a sixth diagram type.

### Bulk org-standards upload in Knowledge

Standards are added one at a time today. Once Governance compliance
evidence depends on citing them, uploading several at once matters more.

## Next

### Real cost modeling

Options currently show a static Low/Medium/High cost band per template.
Replace it with an actual estimate computed from the stack and scale
evidence captured in interview, feeding the same Cost awareness category
above.

### Shared/team deploy mode

Multi-user accounts and roles on the same self-hosted stack — still no
SaaS. This is the item where the local-first-vs-team tension actually
surfaces in practice.

### GitHub-native export target

Alongside the existing zip download, open a pull request against a
connected repository with the generated package files.

## Later

### Brownfield import

Point Archavow at an existing repository and reverse-derive a starting
HLD/diagram set, instead of requiring a blank-slate intake.

### Jira/Confluence sync

Push delivery backlog items to Jira, or HLD/ADRs to Confluence, for teams
whose system of record lives outside Archavow.

### Threaded review/comments on ADRs and diagrams

Real discussion threads attached to specific artifacts — deeper than
shared access alone.

### Hosted/SaaS tier

An open question, not a commitment — see above.
