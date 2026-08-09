import { ApiUnavailable } from "@/components/ApiUnavailable";
import { AppShell } from "@/components/AppShell";
import { Reveal } from "@/components/Reveal";
import { getAISettings, getHealth } from "@/lib/api";
import { AISettingsForm } from "./AISettingsForm";

export default async function SettingsPage() {
  let error: string | null = null;
  let settings: Awaited<ReturnType<typeof getAISettings>> | null = null;
  let health: Awaited<ReturnType<typeof getHealth>> | null = null;

  try {
    [settings, health] = await Promise.all([getAISettings(), getHealth()]);
  } catch (err) {
    error = err instanceof Error ? err.message : "Failed to load settings";
  }

  return (
    <AppShell>
      <Reveal>
        <h1>Settings</h1>
        <p className="lede">
          Choose chat and embedding providers independently. API keys stay in
          environment variables — never in the database.
        </p>
      </Reveal>

      {error ? <ApiUnavailable detail={error} /> : null}

      {health ? (
        <Reveal delay={0.05}>
          <section className="panel blueprint">
            <i className="corner tl" />
            <i className="corner tr" />
            <i className="corner bl" />
            <i className="corner br" />
            <h2>System</h2>
            <p className="muted" style={{ marginTop: 0 }}>
              API status: <strong>{health.status}</strong>
              {" · "}
              Postgres:{" "}
              <span className={health.postgres.ok ? "tag tag-ok" : "tag tag-bad"}>
                {health.postgres.ok ? "ok" : "down"}
              </span>
            </p>
          </section>
        </Reveal>
      ) : null}

      {settings ? (
        <Reveal delay={0.1}>
          <section className="panel blueprint">
            <i className="corner tl" />
            <i className="corner tr" />
            <i className="corner bl" />
            <i className="corner br" />
            <h2>AI providers</h2>
            <p className="muted" style={{ marginTop: 0 }}>
              Chat: Ollama or OpenAI. Embeddings: Ollama, OpenAI, or{" "}
              <strong>none</strong> (keyword retrieval only). Dimensions
              default to 768 for pgvector.
            </p>
            <AISettingsForm initial={settings} />
          </section>
        </Reveal>
      ) : null}
    </AppShell>
  );
}
