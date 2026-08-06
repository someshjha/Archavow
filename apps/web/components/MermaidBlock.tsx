"use client";

import { useEffect, useId, useState } from "react";

type Props = {
  title: string;
  source: string;
};

let mermaidReady: Promise<typeof import("mermaid").default> | null = null;

/** Mermaid 11 renames / common model mistakes */
function sanitizeMermaidSource(raw: string): string {
  return raw
    .replace(/\bContainer_Queue\b/g, "ContainerQueue")
    .replace(/—/g, "-")
    .replace(/·/g, "-")
    .trim();
}

/** Defense in depth: strip scriptable SVG even if Mermaid emits it.
 *
 * Mermaid 11 puts flowchart node labels inside <foreignObject>. We keep those
 * (otherwise every box renders empty) but strip scripts, handlers, and
 * javascript: URLs from inside them.
 */
function sanitizeSvg(svg: string): string {
  const scrub = (html: string) =>
    html
      .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "")
      .replace(/\son[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
      .replace(/javascript:/gi, "")
      .replace(/data:text\/html/gi, "");

  return scrub(svg).replace(
    /<foreignObject\b([^>]*)>([\s\S]*?)<\/foreignObject>/gi,
    (_match, attrs: string, body: string) =>
      `<foreignObject${attrs}>${scrub(body)}</foreignObject>`,
  );
}

function loadMermaid() {
  if (!mermaidReady) {
    mermaidReady = import("mermaid").then((mod) => {
      const mermaid = mod.default;
      mermaid.initialize({
        startOnLoad: false,
        // AI/user diagram sources must not run scripts or foreignObject HTML
        securityLevel: "strict",
        // Prefer our error-box over Mermaid's bomb SVG
        suppressErrorRendering: true,
        theme: "base",
        themeVariables: {
          primaryColor: "#eef2f7",
          primaryTextColor: "#1a1f2c",
          primaryBorderColor: "#3d5a80",
          lineColor: "#4a5568",
          secondaryColor: "#fff8f0",
          tertiaryColor: "#ffffff",
          fontFamily: "IBM Plex Sans, 'Segoe UI', sans-serif",
          fontSize: "14px",
          actorBkg: "#e8efe9",
          actorBorder: "#2f5d50",
          actorTextColor: "#1c2a24",
          signalColor: "#1a1f2c",
          labelBoxBkgColor: "#fffdf8",
          labelBoxBorderColor: "#c45c26",
        },
        flowchart: {
          curve: "basis",
          padding: 16,
          // Mermaid 11 still emits foreignObject for node labels; we sanitize
          // those in sanitizeSvg instead of disabling HTML labels (which left
          // empty boxes once FO was stripped).
          htmlLabels: true,
        },
        sequence: {
          actorMargin: 48,
          messageMargin: 40,
          mirrorActors: false,
        },
        c4: {
          diagramMarginX: 40,
          diagramMarginY: 32,
          c4ShapeMargin: 28,
          c4ShapePadding: 12,
          width: 220,
          height: 90,
          personFontSize: 13,
          personFontFamily: "IBM Plex Sans, sans-serif",
          systemFontSize: 13,
          containerFontSize: 12,
          componentFontSize: 12,
          boundaryFontSize: 12,
        },
      });
      return mermaid;
    });
  }
  return mermaidReady;
}

export function MermaidBlock({ title, source }: Props) {
  const reactId = useId().replace(/:/g, "");
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSource, setShowSource] = useState(false);
  const cleaned = sanitizeMermaidSource(source);

  useEffect(() => {
    let cancelled = false;
    setSvg(null);
    setError(null);
    (async () => {
      try {
        const mermaid = await loadMermaid();
        // Validate first so we never paint Mermaid's bomb graphic
        await mermaid.parse(cleaned);
        const { svg: rendered } = await mermaid.render(
          `mmd-${reactId}-${Math.random().toString(36).slice(2, 8)}`,
          cleaned,
        );
        if (!cancelled) setSvg(sanitizeSvg(rendered));
      } catch (err) {
        if (!cancelled) {
          const msg =
            err instanceof Error
              ? err.message
              : typeof err === "string"
                ? err
                : "Mermaid render failed";
          setError(msg.replace(/\s+/g, " ").slice(0, 240));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reactId, cleaned]);

  return (
    <section className="mermaid-block" style={{ marginTop: 24 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <h2 style={{ fontSize: 16, margin: 0 }}>{title}</h2>
        <button
          type="button"
          className="btn"
          style={{ padding: "4px 10px", fontSize: 13 }}
          onClick={() => setShowSource((v) => !v)}
        >
          {showSource ? "Hide source" : "Show source"}
        </button>
      </div>
      {error ? (
        <div className="error-box" role="alert" style={{ marginTop: 12 }}>
          Could not render diagram. {error}
        </div>
      ) : null}
      {!error && !svg ? (
        <p className="muted" style={{ marginTop: 12 }}>
          Rendering diagram…
        </p>
      ) : null}
      {svg ? (
        <div
          className="mermaid-canvas blueprint"
          style={{ marginTop: 12 }}
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      ) : null}
      {showSource || error ? (
        <pre className="doc-block" style={{ marginTop: 12 }}>
          {cleaned}
        </pre>
      ) : null}
    </section>
  );
}
