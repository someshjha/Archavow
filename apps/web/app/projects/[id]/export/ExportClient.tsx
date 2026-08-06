"use client";

import Link from "next/link";
import { useMemo, useState, useTransition } from "react";

type ExportFile = { path: string; content: string };

type ExportResult = {
  id: string;
  layout: string;
  status: string;
  files: ExportFile[];
};

export function ExportClient({ projectId }: { projectId: string }) {
  const [includeHld, setIncludeHld] = useState(true);
  const [includeMermaid, setIncludeMermaid] = useState(true);
  const [includeAdrs, setIncludeAdrs] = useState(true);
  const [includeRisks, setIncludeRisks] = useState(true);
  const [includeProjectJson, setIncludeProjectJson] = useState(true);
  const [layout, setLayout] = useState<"folder" | "zip">("folder");
  const [result, setResult] = useState<ExportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const treePreview = useMemo(() => {
    const lines = ["export/", "  README.md"];
    if (includeHld) lines.push("  hld/");
    if (includeMermaid) lines.push("  diagrams/*.mmd");
    if (includeAdrs) lines.push("  decisions/*.md");
    if (includeRisks) lines.push("  risks/*.md");
    if (includeProjectJson) lines.push("  project.json");
    lines.push("  review/architecture-review.md");
    return lines.join("\n");
  }, [
    includeHld,
    includeMermaid,
    includeAdrs,
    includeRisks,
    includeProjectJson,
  ]);

  function createExport() {
    setError(null);
    startTransition(async () => {
      try {
        const res = await fetch(`/api/backend/projects/${projectId}/exports`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            layout,
            include_hld: includeHld,
            include_mermaid: includeMermaid,
            include_adrs: includeAdrs,
            include_risks: includeRisks,
            include_project_json: includeProjectJson,
          }),
        });
        if (!res.ok) throw new Error(await res.text());
        const body = (await res.json()).data as ExportResult;
        setResult(body);

        if (layout === "zip") {
          const dl = await fetch(
            `/api/backend/projects/${projectId}/exports/${body.id}/download`,
          );
          if (!dl.ok) throw new Error(await dl.text());
          const blob = await dl.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `archavow-export-${body.id.slice(0, 8)}.zip`;
          a.click();
          URL.revokeObjectURL(url);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Export failed");
      }
    });
  }

  function downloadFolderAsZip() {
    if (!result) return;
    startTransition(async () => {
      try {
        const dl = await fetch(
          `/api/backend/projects/${projectId}/exports/${result.id}/download`,
        );
        if (!dl.ok) throw new Error(await dl.text());
        const blob = await dl.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `archavow-export-${result.id.slice(0, 8)}.zip`;
        a.click();
        URL.revokeObjectURL(url);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Download failed");
      }
    });
  }

  return (
    <div className="export-page">
      {error ? (
        <div className="error-box" role="alert">
          {error}
        </div>
      ) : null}

      <div className="card blueprint export-card">
        <i className="corner tl" />
        <i className="corner tr" />
        <i className="corner bl" />
        <i className="corner br" />

        <div className="card-kicker" style={{ marginBottom: 4 }}>
          Contents
        </div>
        <label className="chk">
          <input
            type="checkbox"
            checked={includeHld}
            onChange={(e) => setIncludeHld(e.target.checked)}
          />
          HLD Markdown
        </label>
        <label className="chk">
          <input
            type="checkbox"
            checked={includeMermaid}
            onChange={(e) => setIncludeMermaid(e.target.checked)}
          />
          Mermaid sources
        </label>
        <label className="chk">
          <input
            type="checkbox"
            checked={includeAdrs}
            onChange={(e) => setIncludeAdrs(e.target.checked)}
          />
          ADRs
        </label>
        <label className="chk">
          <input
            type="checkbox"
            checked={includeRisks}
            onChange={(e) => setIncludeRisks(e.target.checked)}
          />
          Risks
        </label>
        <label className="chk">
          <input
            type="checkbox"
            checked={includeProjectJson}
            onChange={(e) => setIncludeProjectJson(e.target.checked)}
          />
          Project JSON
        </label>

        <div className="export-divider" />

        <div className="card-kicker" style={{ marginBottom: 4 }}>
          Layout
        </div>
        <label className="rad">
          <input
            type="radio"
            name="lay"
            checked={layout === "zip"}
            onChange={() => setLayout("zip")}
          />
          Single zip
        </label>
        <label className="rad">
          <input
            type="radio"
            name="lay"
            checked={layout === "folder"}
            onChange={() => setLayout("folder")}
          />
          Git-friendly folder
        </label>

        <pre className="export-tree">{treePreview}</pre>

        <div className="form-actions" style={{ marginTop: 16 }}>
          <Link href={`/projects/${projectId}/package`} className="btn">
            Cancel
          </Link>
          <button
            type="button"
            className="btn btn-primary"
            disabled={pending}
            onClick={createExport}
          >
            {pending ? "Exporting…" : "Download"}
          </button>
        </div>
      </div>

      {result ? (
        <div className="panel blueprint">
          <i className="corner tl" />
          <i className="corner tr" />
          <i className="corner bl" />
          <i className="corner br" />
          <h2 style={{ fontSize: 18, marginTop: 0 }}>
            Export ready · {result.files.length} files
          </h2>
          <ul className="export-file-list">
            {result.files.map((f) => (
              <li key={f.path}>
                <code>{f.path}</code>
              </li>
            ))}
          </ul>
          <div className="form-actions">
            <button
              type="button"
              className="btn btn-primary"
              disabled={pending}
              onClick={downloadFolderAsZip}
            >
              Download zip
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
