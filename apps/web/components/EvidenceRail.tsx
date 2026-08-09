"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Bar, noteFor, toneFor } from "@/components/CompletenessBars";
import type { Completeness } from "@/lib/api";

type Status = "loading" | "ready" | "unavailable";

/**
 * Coverage used to only appear inside the Interview page. It's the product's
 * actual trust signal (evidence boundaries, not a vibe), so it stays visible
 * from every stage instead — fetched independently of whatever the page
 * itself is loading, so a slow/failed page load never hides it.
 */
export function EvidenceRail({ projectId }: { projectId: string }) {
  const [status, setStatus] = useState<Status>("loading");
  const [completeness, setCompleteness] = useState<Completeness | null>(null);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    (async () => {
      try {
        const res = await fetch(
          `/api/backend/projects/${projectId}/interview`,
          { cache: "no-store" },
        );
        if (!res.ok) throw new Error(String(res.status));
        const body = await res.json();
        if (cancelled) return;
        setCompleteness((body.data?.completeness as Completeness) ?? null);
        setStatus("ready");
      } catch {
        if (!cancelled) setStatus("unavailable");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  return (
    <aside
      className={`workspace-evidence${collapsed ? " is-collapsed" : ""}`}
    >
      <div className="we-head">
        <span className="card-kicker" style={{ margin: 0 }}>
          Evidence &amp; coverage
        </span>
        <button
          type="button"
          className="we-collapse"
          onClick={() => setCollapsed((c) => !c)}
          aria-expanded={!collapsed}
          aria-label={collapsed ? "Expand evidence rail" : "Collapse evidence rail"}
        >
          {collapsed ? "+" : "−"}
        </button>
      </div>

      {collapsed ? null : status === "loading" ? (
        <p className="muted we-note">Loading…</p>
      ) : status === "unavailable" || !completeness ? (
        <p className="muted we-note">
          Coverage appears once intake is saved.
        </p>
      ) : (
        <>
          <div className="bars">
            <Bar label="Overall" value={completeness.overall} emphasis />
            {completeness.categories.map((cat) => (
              <Bar
                key={cat.key}
                label={cat.label}
                value={cat.score}
                tone={toneFor(cat)}
                note={noteFor(cat)}
              />
            ))}
          </div>
          <Link
            href={`/projects/${projectId}/interview`}
            className="we-link"
          >
            {completeness.ready ? "Review interview →" : "Close gaps →"}
          </Link>
        </>
      )}
    </aside>
  );
}
