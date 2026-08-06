"use client";

import { useState } from "react";
import { MermaidBlock } from "@/components/MermaidBlock";

type DiagramKind =
  | "context"
  | "container"
  | "component"
  | "sequence"
  | "dataflow";

const DIAGRAMS: { id: DiagramKind; label: string }[] = [
  { id: "context", label: "L1 Context" },
  { id: "container", label: "L2 Containers" },
  { id: "component", label: "L3 Components" },
  { id: "sequence", label: "Sequence" },
  { id: "dataflow", label: "Data flow" },
];

export function DiagramsClient({
  sources,
}: {
  sources: Partial<Record<DiagramKind, string | undefined>>;
}) {
  const firstAvailable =
    DIAGRAMS.find((d) => sources[d.id])?.id ?? DIAGRAMS[0].id;
  const [selected, setSelected] = useState<DiagramKind>(firstAvailable);
  const active = DIAGRAMS.find((d) => d.id === selected)!;
  const activeSource = sources[selected];

  return (
    <div
      className="diagrams-layout"
      style={{
        display: "grid",
        gridTemplateColumns: "200px 1fr",
        gap: 24,
        alignItems: "start",
      }}
    >
      <div className="card blueprint dlist" style={{ padding: 12 }}>
        <i className="corner tl" />
        <i className="corner tr" />
        <i className="corner bl" />
        <i className="corner br" />
        <div className="card-kicker" style={{ marginBottom: 8 }}>
          Diagrams
        </div>
        {DIAGRAMS.map((d) => {
          const present = Boolean(sources[d.id]);
          return (
            <button
              key={d.id}
              type="button"
              onClick={() => setSelected(d.id)}
              className={d.id === selected ? "on" : ""}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                width: "100%",
                padding: "6px 10px",
                fontSize: 13,
                textAlign: "left",
                background:
                  d.id === selected
                    ? "color-mix(in srgb, var(--color-text, #1c2a24) 5%, transparent)"
                    : "transparent",
                border: "none",
                cursor: present ? "pointer" : "default",
                opacity: present ? 1 : 0.45,
                color: "inherit",
                font: "inherit",
              }}
              disabled={!present}
            >
              {d.label}
              <span className={`tag ${present ? "tag-ok" : ""}`}>
                {present ? "✓" : "—"}
              </span>
            </button>
          );
        })}
      </div>

      <div>
        {activeSource ? (
          <MermaidBlock title={active.label} source={activeSource} />
        ) : (
          <p className="muted">
            This diagram was not generated for the current package. Regenerate
            the package after selecting an option.
          </p>
        )}
      </div>
    </div>
  );
}
