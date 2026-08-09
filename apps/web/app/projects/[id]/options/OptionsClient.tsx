"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

type OptionDesign = {
  approach?: string;
  assumptions?: string[];
  constraints?: string[];
  key_decisions?: string[];
};

type Option = {
  id: string;
  key?: string;
  title: string;
  summary: string;
  pros: string[];
  cons: string[];
  fit_score: number;
  cost_band: string;
  ops_band: string;
  recommended: boolean;
  selected: boolean;
  stack?: string[];
  origin?: "template" | "ai";
  design?: OptionDesign;
};

export function OptionsClient({ projectId }: { projectId: string }) {
  const router = useRouter();
  const [options, setOptions] = useState<Option[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [aiAssist, setAiAssist] = useState<{ status: string; detail?: string | null } | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [view, setView] = useState<"matrix" | "cards">("matrix");

  function applyPayload(data: {
    options: Option[];
    selected_option_id?: string | null;
    ai_assist?: { status: string; detail?: string | null } | null;
  }) {
    setOptions(data.options);
    setSelectedId(data.selected_option_id ?? null);
    if (data.ai_assist) setAiAssist(data.ai_assist);
  }

  function loadExisting() {
    startTransition(async () => {
      try {
        setError(null);
        const res = await fetch(`/api/backend/projects/${projectId}/options`, {
          cache: "no-store",
        });
        if (!res.ok) throw new Error(await res.text());
        const body = await res.json();
        const existing = (body.data.options as Option[]) || [];
        if (existing.length > 0) {
          applyPayload(body.data);
          return;
        }
        await regenerate();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Load failed");
      }
    });
  }

  async function regenerate() {
    setError(null);
    const gen = await fetch(
      `/api/backend/projects/${projectId}/options/generate`,
      { method: "POST" },
    );
    if (!gen.ok) throw new Error(await gen.text());
    const body = await gen.json();
    applyPayload(body.data);
    setAiAssist(body.data.ai_assist ?? null);
  }

  function onRegenerate() {
    startTransition(async () => {
      try {
        await regenerate();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Generate failed");
      }
    });
  }

  useEffect(() => {
    loadExisting();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function readApiError(res: Response): Promise<string> {
    const raw = await res.text();
    try {
      const body = JSON.parse(raw) as { detail?: unknown };
      if (typeof body.detail === "string") return body.detail;
      if (body.detail != null) return JSON.stringify(body.detail);
    } catch {
      /* plain text */
    }
    return raw || `Request failed (${res.status})`;
  }

  function select(optionId: string) {
    startTransition(async () => {
      try {
        setError(null);
        // Already chosen — open package without wiping it
        if (optionId === selectedId) {
          const existing = await fetch(
            `/api/backend/projects/${projectId}/package`,
            { cache: "no-store" },
          );
          if (existing.ok) {
            router.push(`/projects/${projectId}/package`);
            return;
          }
        }
        const res = await fetch(
          `/api/backend/projects/${projectId}/options/${optionId}/select`,
          { method: "POST" },
        );
        if (!res.ok) {
          const detail = await readApiError(res);
          if (res.status === 404) {
            // Stale option ids after regenerate in another tab — refresh list.
            try {
              const listed = await fetch(
                `/api/backend/projects/${projectId}/options`,
                { cache: "no-store" },
              );
              if (listed.ok) {
                const listedBody = await listed.json();
                applyPayload(listedBody.data);
              }
            } catch {
              /* keep prior list */
            }
            throw new Error(
              "That option is no longer available (options may have been regenerated). Pick again from the list.",
            );
          }
          throw new Error(detail);
        }
        const body = await res.json();
        applyPayload(body.data);
        const pkg = await fetch(
          `/api/backend/projects/${projectId}/package/generate`,
          { method: "POST" },
        );
        if (!pkg.ok) throw new Error(await readApiError(pkg));
        router.push(`/projects/${projectId}/package`);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Select failed");
      }
    });
  }

  const onlyTemplates =
    options.length > 0 && options.every((o) => (o.origin ?? "template") === "template");

  return (
    <div>
      {error ? (
        <div className="error-box" role="alert">
          {error}
        </div>
      ) : null}

      {/* `origin` is persisted per option, so this stays accurate after a reload —
          unlike ai_assist, which only accompanies a fresh generate response. */}
      {onlyTemplates ? (
        <div className="notice-box" role="status">
          <div>
            <strong>These are starter templates, not a tailored proposal.</strong>{" "}
            AI generation did not return usable options, so Archavow fell back to
            generic archetypes that are the same for every project.
            {aiAssist?.detail ? (
              <>
                {" "}
                Reason: <code>{aiAssist.detail}</code>.
              </>
            ) : null}
          </div>
          <button
            type="button"
            className="btn btn-primary"
            style={{ padding: "6px 14px" }}
            disabled={pending}
            onClick={onRegenerate}
          >
            {pending ? "Retrying…" : "Retry AI generation"}
          </button>
        </div>
      ) : null}

      {!onlyTemplates && aiAssist?.status === "ok" ? (
        <div className="tag-row" style={{ marginBottom: 16 }}>
          <span className="tag tag-ok">ai: ok</span>
          <span className="muted" style={{ fontSize: 13 }}>
            Options tailored to this project
          </span>
        </div>
      ) : null}

      {selectedId ? (
        <div className="gate-banner blueprint" style={{ marginBottom: 16 }}>
          <i className="corner tl" />
          <i className="corner tr" />
          <i className="corner bl" />
          <i className="corner br" />
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 12,
              flexWrap: "wrap",
            }}
          >
            <div>
              <strong>Selection saved.</strong> These options stay available —
              regenerate only if you want a fresh set.
            </div>
            <Link
              href={`/projects/${projectId}/package`}
              className="btn btn-primary"
              style={{ padding: "6px 14px" }}
            >
              View package →
            </Link>
          </div>
        </div>
      ) : null}

      {options.length > 0 ? (
        <div
          className="opt-view-toggle"
          role="group"
          aria-label="Options view"
          style={{ marginBottom: 16 }}
        >
          <button
            type="button"
            className={view === "matrix" ? "is-on" : ""}
            onClick={() => setView("matrix")}
            aria-pressed={view === "matrix"}
          >
            Matrix
          </button>
          <button
            type="button"
            className={view === "cards" ? "is-on" : ""}
            onClick={() => setView("cards")}
            aria-pressed={view === "cards"}
          >
            Cards
          </button>
        </div>
      ) : null}

      {view === "matrix" && options.length > 0 ? (
        <div className="opt-matrix-wrap" style={{ marginBottom: 24 }}>
          <table className="opt-matrix">
            <thead>
              <tr>
                <th scope="col" />
                {options.map((opt) => (
                  <th
                    key={opt.id}
                    scope="col"
                    className={opt.selected ? "selected-col" : ""}
                  >
                    <div className="opt-matrix-head">
                      {opt.recommended ? (
                        <span className="tag tag-ok">Recommended</span>
                      ) : null}
                      <button
                        type="button"
                        className={`opt-matrix-select${opt.selected ? " is-selected" : ""}`}
                        onClick={() => select(opt.id)}
                        disabled={pending}
                      >
                        <span className="opt-radio" aria-hidden="true" />
                        <span className="opt-matrix-title">{opt.title}</span>
                      </button>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">Fit score</th>
                {options.map((opt) => (
                  <td key={opt.id} className={opt.selected ? "selected-col" : ""}>
                    {opt.fit_score}
                  </td>
                ))}
              </tr>
              <tr>
                <th scope="row">Cost</th>
                {options.map((opt) => (
                  <td key={opt.id} className={opt.selected ? "selected-col" : ""}>
                    {opt.cost_band || "—"}
                  </td>
                ))}
              </tr>
              <tr>
                <th scope="row">Ops</th>
                {options.map((opt) => (
                  <td key={opt.id} className={opt.selected ? "selected-col" : ""}>
                    {opt.ops_band || "—"}
                  </td>
                ))}
              </tr>
              {options.some((o) => (o.stack || []).length > 0) ? (
                <tr>
                  <th scope="row">Stack</th>
                  {options.map((opt) => (
                    <td key={opt.id} className={opt.selected ? "selected-col" : ""}>
                      {(opt.stack || []).join(", ") || "—"}
                    </td>
                  ))}
                </tr>
              ) : null}
            </tbody>
            <tfoot>
              <tr>
                <td />
                {options.map((opt) => (
                  <td key={opt.id} className={opt.selected ? "selected-col" : ""}>
                    <button
                      type="button"
                      className={`btn ${opt.selected || opt.recommended ? "btn-primary" : ""}`}
                      style={{ width: "100%" }}
                      disabled={pending}
                      onClick={() => select(opt.id)}
                    >
                      {opt.selected ? "Open package" : "Select this"}
                    </button>
                  </td>
                ))}
              </tr>
            </tfoot>
          </table>
        </div>
      ) : null}

      {view === "cards" ? (
      <div className="options-grid">
        {options.map((opt) => (
          <div
            key={opt.id}
            className={`opt blueprint ${opt.recommended ? "rec" : ""} ${
              opt.selected ? "selected" : ""
            }`}
          >
            <i className="corner tl" />
            <i className="corner tr" />
            <i className="corner bl" />
            <i className="corner br" />
            <div className="tag-row">
              <span className={`tag ${opt.recommended ? "tag-ok" : ""}`}>
                {opt.recommended ? "Recommended" : "Alternative"}
              </span>
              {opt.selected ? (
                <span className="tag tag-ok">Selected</span>
              ) : null}
            </div>
            <h2 style={{ fontSize: 20, margin: "8px 0 0" }}>{opt.title}</h2>
            <p className="muted" style={{ margin: 0 }}>
              {opt.summary}
            </p>
            {opt.design?.approach ? (
              <p style={{ margin: "8px 0 0", fontSize: 14 }}>{opt.design.approach}</p>
            ) : null}
            {(opt.design?.assumptions?.length ||
              opt.design?.constraints?.length ||
              opt.design?.key_decisions?.length) ? (
              <div className="tradeoffs" style={{ marginTop: 12 }}>
                {opt.design?.assumptions?.length ? (
                  <div>
                    <div className="card-kicker">Assumptions</div>
                    <ul className="tradeoff-list">
                      {opt.design.assumptions.map((a) => (
                        <li key={a}>{a}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {opt.design?.constraints?.length ? (
                  <div>
                    <div className="card-kicker">Constraints</div>
                    <ul className="tradeoff-list">
                      {opt.design.constraints.map((c) => (
                        <li key={c}>{c}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {opt.design?.key_decisions?.length ? (
                  <div>
                    <div className="card-kicker">Key decisions</div>
                    <ul className="tradeoff-list">
                      {opt.design.key_decisions.map((d) => (
                        <li key={d}>{d}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ) : null}
            <div className="tradeoffs">
              <div>
                <div className="card-kicker">Pros</div>
                <ul className="tradeoff-list pros">
                  {(opt.pros?.length ? opt.pros : ["—"]).map((p) => (
                    <li key={p}>
                      <strong>+</strong> {p}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="card-kicker">Cons</div>
                <ul className="tradeoff-list cons">
                  {(opt.cons?.length ? opt.cons : ["—"]).map((c) => (
                    <li key={c}>
                      <strong>−</strong> {c}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              Fit score {opt.fit_score} · Cost {opt.cost_band} · Ops {opt.ops_band}
            </div>
            <button
              type="button"
              className={`btn ${opt.selected || opt.recommended ? "btn-primary" : ""}`}
              style={{ width: "100%", marginTop: 8 }}
              disabled={pending}
              onClick={() => select(opt.id)}
            >
              {opt.selected ? "Open package" : "Select this"}
            </button>
          </div>
        ))}
      </div>
      ) : null}

      {!options.length && pending ? (
        <p className="muted">Loading architecture options…</p>
      ) : null}

      {!selectedId ? (
        <div className="gate-banner blueprint">
          <i className="corner tl" />
          <i className="corner tr" />
          <i className="corner bl" />
          <i className="corner br" />
          <div>
            <strong>Human gate.</strong> After you select, Archavow generates the
            HLD and context diagram from this option — not before.
          </div>
        </div>
      ) : null}

      <div className="form-actions">
        <Link href={`/projects/${projectId}/interview`} className="btn">
          Back to interview
        </Link>
        <button
          type="button"
          className="btn"
          disabled={pending}
          onClick={onRegenerate}
        >
          Regenerate options
        </button>
      </div>
    </div>
  );
}
