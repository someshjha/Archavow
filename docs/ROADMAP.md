# Roadmap

This is a working roadmap, not a commitment schedule or a delivery date
sheet. Items are grouped by how soon they're likely to land, and every item
traces to something Archavow already says about itself — an explicit
exclusion in [README.md's Scope section](../README.md#scope), a live
evidence-coverage state visible on the Dashboard today, or a checkpoint
already noted in [docs/DEMO.md](DEMO.md). Nothing here is speculative
feature brainstorming disconnected from the current product.

| Status | Item | Why it's here |
|---|---|---|
| **Now** | [Evidence-gap remediation + pre-export completeness checkpoint](#evidence-gap-remediation--pre-export-completeness-checkpoint) | 7 of 10 Dashboard evidence categories have no interview question backing them and can never reach `verified` |
| **Now** | [Deployment/infra topology diagram](#deploymentinfra-topology-diagram) | Explicitly called out as missing from the diagram set in the guided demo |
| **Now** | [Bulk org-standards upload in Knowledge](#bulk-org-standards-upload-in-knowledge) | Governance compliance evidence will start depending on citing standards more often |
| **Next** | [Real cost modeling](#real-cost-modeling) | Options show a fixed cost label today, not a project-specific estimate |
| **Next** | [Shared/team deploy mode](#sharedteam-deploy-mode) | First real step past single-user, still self-hosted |
| **Next** | [GitHub-native export target](#github-native-export-target) | Export already claims to be Git-ready; this lands it in Git directly |
| **Later** | [Brownfield import](#brownfield-import) | Extends Archavow past greenfield-only intake |
| **Later** | [Jira/Confluence sync](#jiraconfluence-sync) | For teams whose system of record lives outside Archavow |
| **Later** | [Threaded review/comments](#threaded-reviewcomments-on-adrs-and-diagrams) | Deeper collaboration than shared access alone |
| **Later** | [Hosted/SaaS tier](#hostedsaas-tier) | Open question — not a commitment |

## Open question: local-first vs. team use

Archavow is [local-first](../README.md#why-archavow) today: one Docker
Compose stack, one organization's local data, nothing leaves the machine
unless a provider like OpenAI is explicitly configured. Several items below
— shared deploy mode, threaded review, a possible hosted tier — move toward
multi-user and collaborative use, which implies a shared backend somewhere.
That tension is **not resolved by this roadmap**. Near-term (Now) items
stay local-first-safe no matter how it's eventually decided, and the
"Later" items that touch it say so explicitly rather than quietly assuming
an answer.

---

## Now

### Evidence-gap remediation + pre-export completeness checkpoint

**The problem, as it exists in the code today:** the Dashboard's evidence
checklist scores ten categories — requirements completeness, scalability,
reliability, security, operability, data architecture, integration design,
maintainability, cost awareness, governance compliance — each weighted and
each reported as `missing` / `partial` / `evidenced` / `verified`. Only
three of the ten (requirements completeness, reliability, security) are
actually confirmed by an interview answer and can reach `verified`. The
other seven are matched against whatever free text already happens to
exist and are capped at `evidenced` forever — there's no question that
targets them, and no guided way for a user to close them intentionally.

**What ships:**

- Every `missing`/`partial` category on the Dashboard gets a **Close this
  gap →** action. Six of the seven uncapped categories (operability, cost
  awareness, maintainability, data architecture, integration design,
  scalability) reopen Interview with one new targeted question each, built
  around the same evidence the scorer already looks for — an Operability
  question asks about on-call rotation, runbooks, SLOs, and observability,
  because those are the exact signals the checklist checks for today.
- Governance compliance is the exception: its evidence comes from citing
  an org standard in Knowledge, not from interview text, so its action
  opens Knowledge instead of Interview.
- All six interview-backed categories gain a real interview cap, so they
  can reach `verified` for the first time — closing the gap the problem
  statement above describes.
- **Before Export runs**, a completeness checkpoint reads the same ten
  categories and, if any remain `missing`/`partial`, shows exactly which
  ones and why — reusing the checklist's existing reason strings (e.g.
  "No operability / observability evidence in interview") rather than a
  vague warning. Two explicit choices follow: **close the gaps now**, or
  **export anyway**. This stays advisory, never a hard block — consistent
  with evidence coverage already being reported as a checklist, not a
  certification score, and with the existing rule that a human decision
  (not the tool) gates package generation.
- Closing a gap after Package/Export already exist doesn't silently
  regenerate anything downstream. Affected artifacts are flagged
  **"evidence changed since generation"**, with an explicit **Recreate
  package** action the user has to choose — nothing rewrites a decision
  behind anyone's back.

### Deployment/infra topology diagram

The current diagram set — C4 context, container, component, sequence, and
data-flow — stops at the logical/behavioral layer of the C4 model. It never
shows where things actually run: which compute target hosts which service,
where the network boundary between public edge and internal services sits,
or where the datastore and event bus physically live. A deployment diagram
is the natural next diagram in the same C4 vocabulary the app already
uses, generated from the same option/stack data that drives the existing
five.

### Bulk org-standards upload in Knowledge

Org standards are added to Knowledge one file at a time today. Once
[Governance compliance evidence](#evidence-gap-remediation--pre-export-completeness-checkpoint)
starts depending on citing them, that friction shows up more often. This
item batches the existing single-file ingestion path — same chunking and
embedding pipeline, just accepting a multi-file selection instead of one
file per action.

---

## Next

*(~6 months out — bigger lift than Now, still grounded in an existing gap rather than a new idea.)*

### Real cost modeling

Options currently render a fixed `cost_band` (Low / Medium / High) baked
into each option template, regardless of the actual project. This replaces
that fixed label with an estimate computed from evidence already captured
— the stack list and scale/peak-traffic evidence from interview — feeding
the same [Cost awareness category](#evidence-gap-remediation--pre-export-completeness-checkpoint)
above. Like the rest of the evidence model, the output should carry an
explicit confidence label (the checklist already distinguishes
`medium`/`low` confidence elsewhere) rather than presenting a bare number
with false precision.

### Shared/team deploy mode

Multi-user accounts and roles — for example, an architect who can edit, a
reviewer who can comment or approve, a viewer who's read-only — layered
onto the same self-hosted Postgres/Docker Compose stack. Still no hosted
component and no SaaS. This is the item where the
[local-first-vs-team tension](#open-question-local-first-vs-team-use)
actually surfaces in practice, not just in theory.

### GitHub-native export target

Alongside the existing zip download, choose a connected repository and
branch and open a pull request containing the generated package files
directly. The PR description reuses the same commit-style summary line
already computed for zip exports (`N files · M ADRs · K diagrams`) instead
of inventing new summary text — it extends an existing pattern rather than
adding a second one.

---

## Later

*(Bigger, less certain bets — direction, not a schedule.)*

### Brownfield import

Point Archavow at an existing repository and derive a starting HLD and C4
diagram set from its structure and dependencies, instead of requiring a
blank-slate intake every time. Consistent with the product's existing
human-in-the-loop stance, the result is a **draft** an architect reviews
and edits — it does not carry the same weight as an interview-confirmed
answer until a person accepts it.

### Jira/Confluence sync

Push the delivery backlog's epics and stories to Jira, or the HLD/ADRs to
Confluence, for teams whose system of record lives outside Archavow.
One-way (Archavow → target) only at first, to avoid the conflict handling
a two-way sync would require. Pushed Jira issues would carry their source
`R-00N` requirement reference in the description, so traceability survives
the export.

### Threaded review/comments on ADRs and diagrams

Comments attach to a specific artifact section, not the whole document,
with an open/resolved state — async only, no live cursors or presence.
Deeper than the access-only collaboration in
[shared/team deploy mode](#sharedteam-deploy-mode), but still short of the
real-time collaborative editing the README's Scope section already rules
out.

### Hosted/SaaS tier

An open question, not a commitment — see
[local-first vs. team use](#open-question-local-first-vs-team-use) above.
If it's ever pursued, [shared/team deploy mode](#sharedteam-deploy-mode)
proving real multi-user demand on the self-hosted path would be the
trigger to consider it, not a decision made ahead of that evidence.
