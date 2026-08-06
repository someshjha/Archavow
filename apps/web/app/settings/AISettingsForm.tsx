"use client";

import { useState, useTransition } from "react";
import type { AISettings, AISettingsUpdate, ProbeResult } from "@/lib/api";

async function saveSettings(update: AISettingsUpdate): Promise<AISettings> {
  const res = await fetch("/api/backend/settings/ai", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update),
  });
  if (!res.ok) throw new Error(await res.text());
  const body = await res.json();
  return body.data as AISettings;
}

async function runProbe(kind: "chat" | "embeddings"): Promise<ProbeResult> {
  const res = await fetch(`/api/backend/settings/ai/probe/${kind}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await res.text());
  const body = await res.json();
  return body.data as ProbeResult;
}

export function AISettingsForm({ initial }: { initial: AISettings }) {
  const [form, setForm] = useState(initial);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [chatProbe, setChatProbe] = useState<ProbeResult | null>(null);
  const [embedProbe, setEmbedProbe] = useState<ProbeResult | null>(null);
  const [pending, startTransition] = useTransition();

  function patch<K extends keyof AISettings>(key: K, value: AISettings[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function onSave() {
    setError(null);
    setMessage(null);
    startTransition(async () => {
      try {
        const saved = await saveSettings({
          chat_provider: form.chat_provider,
          chat_model: form.chat_model,
          embedding_provider: form.embedding_provider,
          embedding_model: form.embedding_model,
          embedding_dimensions: 768,
          ollama_base_url: form.ollama_base_url,
          openai_base_url: form.openai_base_url,
        });
        setForm(saved);
        setMessage("Saved workspace AI settings.");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Save failed");
      }
    });
  }

  function onProbeChat() {
    setError(null);
    startTransition(async () => {
      try {
        setChatProbe(await runProbe("chat"));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Chat probe failed");
      }
    });
  }

  function onProbeEmbed() {
    setError(null);
    startTransition(async () => {
      try {
        setEmbedProbe(await runProbe("embeddings"));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Embed probe failed");
      }
    });
  }

  return (
    <div>
      {error ? (
        <div className="error-box" role="alert">
          {error}
        </div>
      ) : null}
      {message ? <p className="muted">{message}</p> : null}

      <div className="form-grid">
        <div className="form-row">
          <div className="field">
            <label htmlFor="chat_provider">Chat provider</label>
            <select
              id="chat_provider"
              value={form.chat_provider}
              onChange={(e) =>
                patch("chat_provider", e.target.value as AISettings["chat_provider"])
              }
            >
              <option value="ollama">Ollama</option>
              <option value="openai">OpenAI</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="chat_model">Chat model</label>
            <input
              id="chat_model"
              value={form.chat_model}
              onChange={(e) => patch("chat_model", e.target.value)}
            />
          </div>
        </div>

        <div className="form-row">
          <div className="field">
            <label htmlFor="embedding_provider">Embedding provider</label>
            <select
              id="embedding_provider"
              value={form.embedding_provider}
              onChange={(e) =>
                patch(
                  "embedding_provider",
                  e.target.value as AISettings["embedding_provider"],
                )
              }
            >
              <option value="none">None (keyword only)</option>
              <option value="ollama">Ollama</option>
              <option value="openai">OpenAI</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="embedding_model">Embedding model</label>
            <input
              id="embedding_model"
              value={form.embedding_model}
              onChange={(e) => patch("embedding_model", e.target.value)}
              disabled={form.embedding_provider === "none"}
            />
          </div>
        </div>

        <div className="form-row">
          <div className="field">
            <label htmlFor="embedding_dimensions">Embedding dimensions</label>
            <input
              id="embedding_dimensions"
              type="number"
              value={768}
              readOnly
              disabled
              title="Fixed at 768 to match the pgvector column"
            />
            <p className="muted" style={{ margin: "6px 0 0", fontSize: 13 }}>
              Fixed at 768 to match the database vector column.
            </p>
          </div>
          <div className="field">
            <label>OpenAI API key</label>
            <p className="muted" style={{ margin: 0 }}>
              {form.openai_api_key_configured ? (
                <span className="tag tag-ok">configured (env)</span>
              ) : (
                <span className="tag">not set — use OPENAI_API_KEY</span>
              )}
            </p>
          </div>
        </div>

        <div className="form-row">
          <div className="field">
            <label htmlFor="ollama_base_url">Ollama base URL</label>
            <input
              id="ollama_base_url"
              value={form.ollama_base_url}
              onChange={(e) => patch("ollama_base_url", e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="openai_base_url">OpenAI base URL</label>
            <input
              id="openai_base_url"
              value={form.openai_base_url}
              onChange={(e) => patch("openai_base_url", e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="form-actions">
        <button
          type="button"
          className="btn btn-primary"
          disabled={pending}
          onClick={onSave}
        >
          Save settings
        </button>
        <button type="button" className="btn" disabled={pending} onClick={onProbeChat}>
          Probe chat
        </button>
        <button type="button" className="btn" disabled={pending} onClick={onProbeEmbed}>
          Probe embeddings
        </button>
      </div>

      {chatProbe ? (
        <div className="probe-box">
          <strong>Chat probe</strong>{" "}
          <span className={chatProbe.ok ? "tag tag-ok" : "tag tag-bad"}>
            {chatProbe.ok ? "ok" : "failed"}
          </span>
          <div className="muted" style={{ marginTop: 8 }}>
            {chatProbe.provider} · {chatProbe.model || "—"} ·{" "}
            {chatProbe.detail || (chatProbe.reachable ? "reachable" : "unreachable")}
          </div>
        </div>
      ) : null}

      {embedProbe ? (
        <div className="probe-box">
          <strong>Embeddings probe</strong>{" "}
          <span className={embedProbe.ok ? "tag tag-ok" : "tag tag-bad"}>
            {embedProbe.ok ? "ok" : "failed"}
          </span>
          <div className="muted" style={{ marginTop: 8 }}>
            {embedProbe.provider} · {embedProbe.model || "—"} ·{" "}
            {embedProbe.detail || (embedProbe.reachable ? "reachable" : "unreachable")}
          </div>
        </div>
      ) : null}
    </div>
  );
}
