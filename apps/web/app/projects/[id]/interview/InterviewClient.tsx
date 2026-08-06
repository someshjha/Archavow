"use client";

import Link from "next/link";
import { useEffect, useRef, useState, useTransition } from "react";
import type {
  ClarificationQuestion,
  Completeness,
  CompletenessCategory,
  InterviewState,
  NextImpact,
  UnlockCheck,
} from "@/lib/api";

const DONE_MESSAGE =
  "All interview gaps are covered. Generate architecture options next — " +
  "the package (including diagrams) follows once you pick one.";

export function InterviewClient({ projectId }: { projectId: string }) {
  const [state, setState] = useState<InterviewState | null>(null);
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<{
    text: string;
    source: "ai" | "template";
  } | null>(null);
  const [history, setHistory] = useState<
    { role: "bot" | "you"; text: string }[]
  >([]);
  const [pending, startTransition] = useTransition();
  const [suggesting, startSuggestTransition] = useTransition();
  const focusErrorRef = useRef<HTMLDivElement>(null);

  function reportError(message: string) {
    setError(message);
    requestAnimationFrame(() => {
      focusErrorRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
      focusErrorRef.current?.focus();
    });
  }

  useEffect(() => {
    startTransition(async () => {
      try {
        setError(null);
        const res = await fetch(
          `/api/backend/projects/${projectId}/interview/analyze`,
          { method: "POST" },
        );
        if (!res.ok) throw new Error(await res.text());
        const body = await res.json();
        const data = body.data as InterviewState;
        setState(data);
        const start: { role: "bot" | "you"; text: string }[] = [];
        if (data.intro) {
          start.push({ role: "bot", text: data.intro });
        }
        if (data.active_question) {
          start.push({ role: "bot", text: data.active_question.prompt });
        } else {
          start.push({ role: "bot", text: DONE_MESSAGE });
        }
        setHistory(start);
      } catch (err) {
        reportError(err instanceof Error ? err.message : "Analyze failed");
      }
    });
  }, [projectId]);

  function suggestAnswer() {
    if (!state?.active_question) return;
    const q = state.active_question;
    startSuggestTransition(async () => {
      try {
        setError(null);
        const res = await fetch(
          `/api/backend/projects/${projectId}/interview/suggest`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question_id: q.id }),
          },
        );
        if (!res.ok) throw new Error(await res.text());
        const body = await res.json();
        const data = body.data as { suggestion: string; source: "ai" | "template" };
        setSuggestion({ text: data.suggestion, source: data.source });
        setAnswer(data.suggestion);
      } catch (err) {
        reportError(err instanceof Error ? err.message : "Suggest failed");
      }
    });
  }

  function send() {
    if (!state?.active_question || !answer.trim()) return;
    const q = state.active_question;
    const text = answer.trim();
    setAnswer("");
    setSuggestion(null);
    setHistory((h) => [...h, { role: "you", text }]);
    startTransition(async () => {
      try {
        setError(null);
        const res = await fetch(
          `/api/backend/projects/${projectId}/interview/answer`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question_id: q.id, answer: text }),
          },
        );
        if (!res.ok) throw new Error(await res.text());
        const body = await res.json();
        const data = body.data as InterviewState & {
          question: ClarificationQuestion;
        };
        setState(data);
        setHistory((h) => {
          const next = [...h];
          if (data.ai_reply) {
            next.push({ role: "bot", text: data.ai_reply });
          }
          if (data.active_question) {
            next.push({ role: "bot", text: data.active_question.prompt });
          } else {
            next.push({ role: "bot", text: DONE_MESSAGE });
          }
          return next;
        });
      } catch (err) {
        reportError(err instanceof Error ? err.message : "Answer failed");
      }
    });
  }

  const comp: Completeness | null = state?.completeness ?? null;
  const impact: NextImpact | null = state?.next_impact ?? null;
  const ready = comp?.ready ?? false;
  const askedCount = (state?.questions || []).length;
  const openCount = (state?.questions || []).filter(
    (q) => q.status === "open",
  ).length;
  const weakest = weakestCategory(comp);

  const focusError =
    error ? (
      <div
        ref={focusErrorRef}
        className="error-box interview-focus-error"
        role="alert"
        tabIndex={-1}
      >
        {error}
      </div>
    ) : null;

  return (
    <div className="interview-layout">
      <div>
        {error ? (
          <div className="error-box" role="alert">
            {error}
          </div>
        ) : null}

        <div className="chat-panel">
          {history.length === 0 && pending ? (
            <p className="muted">Analyzing gaps…</p>
          ) : null}
          {history.map((msg, i) => (
            <div key={i} className={`bubble ${msg.role}`}>
              <strong>{msg.role === "bot" ? "Copilot" : "You"}</strong>
              <br />
              {msg.text}
            </div>
          ))}
          {state?.active_question?.code.startsWith("ai_") ? (
            <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>
              Current question is an AI follow-up.
            </p>
          ) : null}
          {!state?.active_question ? focusError : null}
        </div>

        {state?.active_question ? (
          <>
            {impact || openCount > 0 ? (
              <div className="q-meta">
                <div className="q-meta-chips">
                  {impact ? (
                    <span className="q-chip q-chip-weak">
                      Weakest: {impact.category_label}
                    </span>
                  ) : null}
                  <span className="q-chip">
                    {askedCount - openCount} of {askedCount} answered
                  </span>
                </div>
                {impact && weakest && impact.category_key === weakest.key ? (
                  <p className="q-reason">
                    Asked next because {impact.category_label} is your lowest
                    category
                    {weakest.score < weakest.floor ? " and blocks the gate" : ""}.
                  </p>
                ) : null}
              </div>
            ) : null}

            {focusError}

            <div className="field" style={{ marginTop: 16 }}>
              <label htmlFor="answer">Your answer</label>
              <textarea
                id="answer"
                rows={3}
                value={answer}
                onChange={(e) => {
                  setAnswer(e.target.value);
                  setSuggestion(null);
                }}
                placeholder="Type here… or ask for a suggestion if you're stuck."
              />
              {suggestion ? (
                <p className="muted" style={{ fontSize: 12, marginTop: 4, marginBottom: 0 }}>
                  {suggestion.source === "ai" ? "AI draft" : "Template draft"} — edit
                  before sending, this isn't your real answer yet.
                </p>
              ) : null}
              {impact ? (
                <p className="impact-line">
                  Answering this raises{" "}
                  <strong>
                    {impact.category_label} {impact.category_from} →{" "}
                    {impact.category_to}
                  </strong>{" "}
                  and{" "}
                  <strong>
                    Overall {impact.overall_from} → {impact.overall_to}
                  </strong>
                </p>
              ) : null}
            </div>
            <div className="form-actions">
              <button
                type="button"
                className="btn"
                disabled={suggesting}
                onClick={suggestAnswer}
              >
                {suggesting ? "Drafting…" : "Suggest an answer"}
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={pending || !answer.trim()}
                onClick={send}
              >
                Send
              </button>
            </div>
          </>
        ) : state ? (
          <div className="form-actions">
            {ready ? (
              <Link
                href={`/projects/${projectId}/options`}
                className="btn btn-primary"
              >
                Architecture options →
              </Link>
            ) : (
              <button type="button" className="btn btn-primary" disabled>
                Architecture options → (locked)
              </button>
            )}
          </div>
        ) : null}
      </div>

      <aside className="panel blueprint">
        <i className="corner tl" />
        <i className="corner tr" />
        <i className="corner bl" />
        <i className="corner br" />
        <div className="card-kicker">Completeness</div>
        {comp ? (
          <>
            <div className="bars">
              <Bar label="Overall" value={comp.overall} emphasis />
              {comp.categories.map((cat) => (
                <Bar
                  key={cat.key}
                  label={cat.label}
                  value={cat.score}
                  tone={toneFor(cat)}
                  note={noteFor(cat)}
                />
              ))}
            </div>
            {!ready ? <UnlockList checks={comp.unlock} /> : null}
          </>
        ) : (
          <p className="muted">Loading…</p>
        )}

        <div className="divider" />
        <div className="card-kicker">AI assist</div>
        <div className="tag-row" style={{ marginBottom: 8 }}>
          <span
            className={`tag ${
              state?.ai_assist?.status === "ok" ? "tag-ok" : ""
            }`}
          >
            {state?.ai_assist?.status || "—"}
          </span>
          {(state?.questions || []).some((q) => q.code.startsWith("ai_")) ? (
            <span className="tag">
              {(state?.questions || []).filter((q) => q.code.startsWith("ai_"))
                .length}{" "}
              AI follow-ups
            </span>
          ) : null}
        </div>
        {state?.ai_assist?.status === "failed" ? (
          <p className="muted" style={{ fontSize: 12, margin: 0 }}>
            Chat unreachable — deterministic gaps only. Probe AI in Settings.
          </p>
        ) : null}

        <div className="divider" />
        <div className="card-kicker">Captured</div>
        <div className="tag-row">
          {(comp?.captured || []).map((c) => (
            <span key={c} className="tag tag-ok">
              {c}
            </span>
          ))}
        </div>

        {ready ? (
          <Link
            href={`/projects/${projectId}/options`}
            className="btn btn-primary"
            style={{ marginTop: 20, width: "100%" }}
          >
            Architecture options →
          </Link>
        ) : (
          <button
            type="button"
            className="btn btn-primary"
            style={{ marginTop: 20, width: "100%" }}
            disabled
            title="Close the checks above to unlock architecture options"
          >
            Architecture options → (locked)
          </button>
        )}
      </aside>
    </div>
  );
}

type BarTone = "ok" | "warn" | "bad";

function Bar({
  label,
  value,
  tone = "ok",
  note,
  emphasis = false,
}: {
  label: string;
  value: number;
  tone?: BarTone;
  note?: string | null;
  emphasis?: boolean;
}) {
  return (
    <div className={`bar-block${emphasis ? " bar-block-lead" : ""}`}>
      <div className="bar-label">
        <span>{label}</span>
        <span className="bar-value">{value}</span>
      </div>
      <div className={`bar tone-${tone}`}>
        <span style={{ width: `${Math.max(value, value > 0 ? 2 : 1)}%` }} />
      </div>
      {note ? <p className="bar-note">{note}</p> : null}
    </div>
  );
}

function UnlockList({ checks }: { checks: UnlockCheck[] }) {
  const failing = checks.filter((c) => !c.ok);
  const passing = checks.filter((c) => c.ok);
  const passingByTarget = new Map<number, string[]>();
  for (const check of passing) {
    passingByTarget.set(check.target, [
      ...(passingByTarget.get(check.target) || []),
      check.label,
    ]);
  }

  return (
    <div className="unlock">
      <div className="card-kicker">Before options unlock</div>
      {failing.map((check) => (
        <p key={check.key} className="unlock-row unlock-bad">
          <span aria-hidden="true">✗</span> {check.label} ≥ {check.target}{" "}
          <span className="muted">({check.value})</span>
        </p>
      ))}
      {[...passingByTarget.entries()].map(([target, labels]) => (
        <p key={target} className="unlock-row unlock-ok">
          <span aria-hidden="true">✓</span> {labels.join(", ")} ≥ {target}
        </p>
      ))}
    </div>
  );
}

function toneFor(cat: CompletenessCategory): BarTone {
  if (cat.score >= cat.floor) return "ok";
  return cat.score * 2 < cat.floor ? "bad" : "warn";
}

function noteFor(cat: CompletenessCategory): string | null {
  const open = cat.open_labels.join(", ");
  if (cat.score < cat.floor) {
    return open ? `needs ${cat.floor} · open: ${open}` : `needs ${cat.floor}`;
  }
  return open ? `open: ${open}` : null;
}

function weakestCategory(comp: Completeness | null): CompletenessCategory | null {
  if (!comp || comp.categories.length === 0) return null;
  return comp.categories.reduce((low, cat) => (cat.score < low.score ? cat : low));
}
