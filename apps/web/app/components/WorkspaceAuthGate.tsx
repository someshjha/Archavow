"use client";

import { FormEvent, useEffect, useState } from "react";

type SessionState = {
  authRequired: boolean;
  authenticated: boolean;
};

export function WorkspaceAuthGate({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<SessionState | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/session", { cache: "no-store" });
        const body = (await res.json()) as SessionState;
        if (!cancelled) setSession(body);
      } catch {
        if (!cancelled) setSession({ authRequired: false, authenticated: true });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      const res = await fetch("/api/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ apiKey }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Unlock failed");
      }
      setSession({ authRequired: true, authenticated: true });
      setApiKey("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unlock failed");
    } finally {
      setPending(false);
    }
  }

  if (!session) {
    return (
      <div className="shell">
        <p className="muted">Checking workspace access…</p>
      </div>
    );
  }

  if (session.authRequired && !session.authenticated) {
    return (
      <div className="shell" style={{ maxWidth: 480, margin: "10vh auto" }}>
        <h1 style={{ fontSize: 28, marginBottom: 8 }}>Unlock workspace</h1>
        <p className="lede">
          This deployment requires the shared Archavow API key. Enter it once;
          it stays in an httpOnly session cookie and is never embedded in page
          JavaScript.
        </p>
        <form onSubmit={onSubmit} className="stack" style={{ gap: 12 }}>
          <div className="field">
            <label htmlFor="workspace-api-key">API key</label>
            <input
              id="workspace-api-key"
              type="password"
              autoComplete="current-password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              required
            />
          </div>
          {error ? (
            <div className="error-box" role="alert">
              {error}
            </div>
          ) : null}
          <button type="submit" className="btn btn-primary" disabled={pending}>
            {pending ? "Unlocking…" : "Unlock"}
          </button>
        </form>
      </div>
    );
  }

  return <>{children}</>;
}
