"use client";

import { useEffect, useState, useTransition } from "react";

import { MarkdownBody } from "@/components/MarkdownBody";
import { MermaidBlock } from "@/components/MermaidBlock";

type Doc = {
  id: string;
  title: string;
  source_class: string;
  chunk_count: number;
  status: string;
};

type Citation = {
  citation: string;
  text: string;
  score: number;
  source_class: string;
};

type AskResult = {
  answer: string;
  points: string[];
  pattern_name?: string | null;
  mermaid?: string | null;
  confidence?: number;
  source?: "knowledge" | "model" | "web";
  grounded?: boolean;
  citations: Citation[];
  retrieval_status: string;
  ai_assist?: { status: string; detail?: string | null; fallback?: boolean };
};

function sourceLabel(source?: string) {
  if (source === "web") return "live research (ungrounded)";
  if (source === "model") return "model (ungrounded)";
  return "knowledge library";
}

function libraryTag(sourceClass: string) {
  if (sourceClass === "project") return "project";
  if (sourceClass === "org") return "org";
  return sourceClass;
}

export function KnowledgeClient() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [title, setTitle] = useState("org-standard.md");
  const [content, setContent] = useState(
    "# Standard\n\nDocument your org architecture rules here.\n\n## Example\n\nKafka clients must use mTLS in production.",
  );
  const [query, setQuery] = useState(
    "What is the CQRS pattern and when should I use it?",
  );
  const [askResult, setAskResult] = useState<AskResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function refresh() {
    startTransition(async () => {
      try {
        // Seeds stay hidden — org uploads and project decisions appear
        const res = await fetch("/api/backend/knowledge/documents");
        if (!res.ok) throw new Error(await res.text());
        const body = await res.json();
        setDocs(body.data as Doc[]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Load failed");
      }
    });
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function upload(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    startTransition(async () => {
      try {
        const res = await fetch("/api/backend/knowledge/documents", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title,
            source_class: "org",
            content,
          }),
        });
        if (!res.ok) throw new Error(await res.text());
        setMessage("Org standard uploaded.");
        refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
      }
    });
  }

  function ask(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setAskResult(null);
    startTransition(async () => {
      try {
        const res = await fetch("/api/backend/knowledge/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, limit: 8 }),
        });
        if (!res.ok) throw new Error(await res.text());
        const body = await res.json();
        setAskResult(body.data as AskResult);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ask failed");
      }
    });
  }

  return (
    <div className="knowledge-layout">
      {error ? (
        <div className="error-box" role="alert">
          {error}
        </div>
      ) : null}
      {message ? <p className="muted">{message}</p> : null}

      <form className="panel blueprint" onSubmit={ask}>
        <i className="corner tl" />
        <i className="corner tr" />
        <i className="corner bl" />
        <i className="corner br" />
        <h2>Ask architecture</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Answers are scored from your library and industry guidance. When that
          is thin, the model fills in from practice (and live research when
          available). Pattern questions get a short definition and a diagram when useful.
        </p>
        <div className="field">
          <label htmlFor="kquery">Question</label>
          <input
            id="kquery"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            required
            placeholder="e.g. What is CQRS and when should I use it?"
          />
        </div>
        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={pending}>
            {pending ? "Thinking…" : "Ask"}
          </button>
          {askResult ? (
            <>
              <span className={`tag${askResult.grounded ? " tag-ok" : ""}`}>
                via {sourceLabel(askResult.source)}
              </span>
              {askResult.grounded === false ? (
                <span className="tag tag-bad">not grounded</span>
              ) : null}
              {typeof askResult.confidence === "number" ? (
                <span className="tag">
                  confidence: {Math.round(askResult.confidence * 100)}%
                </span>
              ) : null}
              <span className="tag">
                retrieval: {askResult.retrieval_status}
              </span>
            </>
          ) : null}
        </div>

        {askResult ? (
          <div style={{ marginTop: 20 }}>
            {askResult.grounded === false ? (
              <div className="error-box" role="status" style={{ marginBottom: 12 }}>
                Not grounded in your knowledge base — treat this as unverified
                model or web output, not library evidence.
              </div>
            ) : null}
            {askResult.pattern_name ? (
              <div className="card-kicker" style={{ marginBottom: 8 }}>
                Pattern · {askResult.pattern_name}
              </div>
            ) : null}
            <div className="probe-box" style={{ marginBottom: 12 }}>
              <div className="card-kicker">Answer</div>
              <MarkdownBody>{askResult.answer}</MarkdownBody>
            </div>
            {(askResult.points || []).length > 0 ? (
              <div style={{ marginBottom: 16 }}>
                <div className="card-kicker">Talking points</div>
                <ul className="tradeoff-list" style={{ marginTop: 8 }}>
                  {askResult.points.map((p) => (
                    <li key={p}>
                      <MarkdownBody compact>{p}</MarkdownBody>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {askResult.mermaid ? (
              <div style={{ marginBottom: 16 }}>
                <MermaidBlock
                  title={
                    askResult.pattern_name
                      ? `${askResult.pattern_name} diagram`
                      : "Architecture diagram"
                  }
                  source={askResult.mermaid}
                />
              </div>
            ) : null}
            {(askResult.citations || []).length > 0 ? (
              <>
                <div className="card-kicker">Sources</div>
                <div
                  style={{
                    marginTop: 8,
                    display: "flex",
                    flexDirection: "column",
                    gap: 10,
                  }}
                >
                  {askResult.citations.map((hit, i) => (
                    <div key={`${hit.citation}-${i}`} className="probe-box">
                      <strong>{hit.citation}</strong>{" "}
                      <span className="tag">{hit.source_class}</span>
                      <MarkdownBody compact className="muted">
                        {hit.text}
                      </MarkdownBody>
                    </div>
                  ))}
                </div>
              </>
            ) : null}
          </div>
        ) : null}
      </form>

      <form className="panel blueprint" onSubmit={upload}>
        <i className="corner tl" />
        <i className="corner tr" />
        <i className="corner bl" />
        <i className="corner br" />
        <h2>Upload org standard</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Org documents and project decisions appear below. Industry guidance
          stays searchable but hidden from this list.
        </p>
        <div className="field">
          <label htmlFor="ktitle">Title</label>
          <input
            id="ktitle"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="kcontent">Content</label>
          <textarea
            id="kcontent"
            rows={8}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            required
          />
        </div>
        <div className="form-actions">
          <button type="submit" className="btn" disabled={pending}>
            Upload
          </button>
        </div>
      </form>

      <section>
        <h2 style={{ fontSize: 18, marginBottom: 12 }}>Your library</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {docs.length === 0 ? (
            <p className="muted">
              No org or project documents yet — upload a standard, or generate a
              package to capture decisions.
            </p>
          ) : (
            docs.map((doc) => (
              <div key={doc.id} className="card blueprint knowledge-row">
                <i className="corner tl" />
                <i className="corner tr" />
                <i className="corner bl" />
                <i className="corner br" />
                <div>
                  <div className="card-title" style={{ fontSize: 16 }}>
                    {doc.title}
                  </div>
                  <p className="muted" style={{ margin: "2px 0 0" }}>
                    {doc.chunk_count} chunks · {doc.status}
                  </p>
                </div>
                <span
                  className={`tag ${
                    doc.source_class === "project" ? "" : "tag-ok"
                  }`}
                >
                  {libraryTag(doc.source_class)}
                </span>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
