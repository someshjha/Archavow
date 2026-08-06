"use client";

import Link from "next/link";
import { useEffect, useState, useTransition } from "react";

type Option = {
  id: string;
  title: string;
  summary: string;
  pros: string[];
  cons: string[];
  fit_score: number;
  cost_band: string;
  ops_band: string;
  recommended: boolean;
  selected: boolean;
};

type Adr = {
  id: string;
  title: string;
  status: string;
  context: string;
  decision: string;
  consequences: string[];
};

export function AdvisorClient({ projectId }: { projectId: string }) {
  const [options, setOptions] = useState<Option[]>([]);
  const [optionAId, setOptionAId] = useState<string>("");
  const [optionBId, setOptionBId] = useState<string>("");
  const [compared, setCompared] = useState(false);
  const [rationale, setRationale] = useState("");
  const [accepted, setAccepted] = useState<Adr | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  useEffect(() => {
    startTransition(async () => {
      try {
        const res = await fetch(`/api/backend/projects/${projectId}/options`, {
          cache: "no-store",
        });
        if (!res.ok) throw new Error(await res.text());
        const body = await res.json();
        const opts = (body.data.options as Option[]) || [];
        setOptions(opts);
        setOptionAId(opts[0]?.id ?? "");
        setOptionBId(opts[1]?.id ?? opts[0]?.id ?? "");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Load failed");
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const optionA = options.find((o) => o.id === optionAId);
  const optionB = options.find((o) => o.id === optionBId);

  function runComparison() {
    setError(null);
    setAccepted(null);
    setCompared(true);
  }

  function accept(chosenId: string) {
    const chosen = options.find((o) => o.id === chosenId);
    if (!chosen || !optionA || !optionB) return;
    startTransition(async () => {
      try {
        setError(null);
        const res = await fetch(
          `/api/backend/projects/${projectId}/advisor/accept`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              option_id_a: optionA.id,
              option_id_b: optionB.id,
              chosen_option_id: chosen.id,
              rationale,
            }),
          },
        );
        if (!res.ok) throw new Error(await res.text());
        const body = await res.json();
        setAccepted(body.data.adr as Adr);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Accept failed");
      }
    });
  }

  if (!options.length) {
    return pending ? (
      <p className="muted">Loading options…</p>
    ) : (
      <p className="muted">No options generated yet.</p>
    );
  }

  return (
    <div>
      {error ? (
        <div className="error-box" role="alert">
          {error}
        </div>
      ) : null}

      <div className="card blueprint" style={{ padding: 16, marginBottom: 24 }}>
        <i className="corner tl" />
        <i className="corner tr" />
        <i className="corner bl" />
        <i className="corner br" />
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr auto",
            gap: 16,
            alignItems: "end",
          }}
        >
          <div className="field">
            <label htmlFor="optA">Option A</label>
            <select
              id="optA"
              value={optionAId}
              onChange={(e) => {
                setOptionAId(e.target.value);
                setCompared(false);
              }}
            >
              {options.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.title}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="optB">Option B</label>
            <select
              id="optB"
              value={optionBId}
              onChange={(e) => {
                setOptionBId(e.target.value);
                setCompared(false);
              }}
            >
              {options.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.title}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!optionAId || !optionBId || optionAId === optionBId}
            onClick={runComparison}
          >
            Run comparison
          </button>
        </div>
        {optionAId === optionBId ? (
          <p className="muted" style={{ fontSize: 13, marginTop: 8, marginBottom: 0 }}>
            Pick two different options to compare.
          </p>
        ) : null}
      </div>

      {compared && optionA && optionB ? (
        <>
          <div className="table-scroll" style={{ marginBottom: 24 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Dimension</th>
                  <th>{optionA.title}</th>
                  <th>{optionB.title}</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Fit score</td>
                  <td>{optionA.fit_score}</td>
                  <td>{optionB.fit_score}</td>
                </tr>
                <tr>
                  <td>Cost</td>
                  <td>{optionA.cost_band}</td>
                  <td>{optionB.cost_band}</td>
                </tr>
                <tr>
                  <td>Ops burden</td>
                  <td>{optionA.ops_band}</td>
                  <td>{optionB.ops_band}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="package-split" style={{ marginBottom: 24 }}>
            {[optionA, optionB].map((opt) => (
              <section key={opt.id} className="panel blueprint">
                <i className="corner tl" />
                <i className="corner tr" />
                <i className="corner bl" />
                <i className="corner br" />
                <h2 style={{ fontSize: 16, marginTop: 0 }}>{opt.title}</h2>
                <div className="card-kicker">Pros</div>
                <ul className="tradeoff-list pros">
                  {(opt.pros?.length ? opt.pros : ["—"]).map((p) => (
                    <li key={p}>
                      <strong>+</strong> {p}
                    </li>
                  ))}
                </ul>
                <div className="card-kicker">Cons</div>
                <ul className="tradeoff-list cons">
                  {(opt.cons?.length ? opt.cons : ["—"]).map((c) => (
                    <li key={c}>
                      <strong>−</strong> {c}
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>

          <div className="field" style={{ marginBottom: 16 }}>
            <label htmlFor="rationale">Rationale (optional)</label>
            <textarea
              id="rationale"
              rows={2}
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              placeholder="Why does one option win? Recorded on the ADR."
            />
          </div>

          {accepted ? (
            <div className="gate-banner blueprint">
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
                  width: "100%",
                }}
              >
                <div>
                  <strong>Accepted as {accepted.id}.</strong> Recorded on the
                  package.
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
          ) : (
            <div className="gate-banner blueprint">
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
                  width: "100%",
                }}
              >
                <div>
                  <strong>Human gate.</strong> Nothing is recorded as a
                  decision until you accept it.
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button
                    type="button"
                    className="btn"
                    disabled={pending}
                    onClick={() => accept(optionA.id)}
                  >
                    Accept {optionA.title}
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={pending}
                    onClick={() => accept(optionB.id)}
                  >
                    Accept {optionB.title}
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}
