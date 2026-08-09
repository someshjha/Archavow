import Link from "next/link";
import { ApiUnavailable } from "@/components/ApiUnavailable";
import { AppShell } from "@/components/AppShell";
import { Reveal } from "@/components/Reveal";
import { type LifecycleStage } from "@/components/Stepper";
import { getDashboard, getProject } from "@/lib/api";

type Dashboard = {
  continue_path: string;
  lifecycle: {
    stage: LifecycleStage;
    label: string;
    milestones: Record<string, boolean>;
  };
  quality_score: {
    overall: string;
    categories: {
      id: string;
      label: string;
      weight: number;
      coverage: string;
    }[];
    missing_evidence: string[];
    blockers: string[];
    label: string;
  } | null;
  selected_option: { id: string; title: string; summary: string; fit_score: number } | null;
  decisions: { id: string; title: string; status: string }[];
  open_risks: { id: string; title: string; severity: string; category: string }[];
  backlog: { id: string; title: string; priority: string; area: string }[];
  threats: { id: string; stride: string; asset: string }[];
  package_status: string | null;
};

async function loadDashboard(projectId: string): Promise<Dashboard | null> {
  try {
    return (await getDashboard(projectId)) as Dashboard;
  } catch {
    return null;
  }
}

/** Coverage states are qualitative, not a percentage — tag color is the only
 *  signal, so it has to be accurate: verified/evidenced read as done,
 *  partial as in-progress, missing as not started. */
function coverageTagClass(coverage: string): string {
  if (coverage === "verified" || coverage === "evidenced") return "tag tag-ok";
  if (coverage === "missing") return "tag tag-bad";
  return "tag";
}

function severityTagClass(severity: string): string {
  return severity === "high" ? "tag tag-bad" : "tag";
}

export default async function ProjectDashboardPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [dash, project] = await Promise.all([
    loadDashboard(id),
    getProject(id).catch(() => null),
  ]);
  const reached: LifecycleStage =
    dash?.lifecycle.stage || project?.lifecycle?.stage || "intake";
  const title = project?.name || "Project";

  return (
    <AppShell wide projectId={id} stage={reached} reachedStage={reached}>
      <Reveal>
        <h1>{title}</h1>
        <p className="lede">
          Where things stand: score, decisions, and open risks for this project.
        </p>
      </Reveal>

      {!dash ? (
        <ApiUnavailable action={{ href: "/", label: "Back to projects" }} />
      ) : (
        <Reveal delay={0.08}>
          <div className="panel blueprint" style={{ marginBottom: 24 }}>
            <i className="corner tl" />
            <i className="corner tr" />
            <i className="corner bl" />
            <i className="corner br" />
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 16,
                flexWrap: "wrap",
              }}
            >
              <div className="tag-row">
                <span className="tag tag-ok">{dash.lifecycle.label}</span>
                {dash.package_status ? (
                  <span className="tag">package: {dash.package_status}</span>
                ) : null}
                {dash.selected_option ? (
                  <span className="tag tag-ok">
                    Option: {dash.selected_option.title}
                  </span>
                ) : null}
              </div>
              {/* Interview/Options/Package/Export already live in the stage
                  rail on the left — repeating them here was pure duplication.
                  Diagrams and Advisor aren't rail stages, so they stay. */}
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Link href={dash.continue_path} className="btn btn-primary">
                  Continue →
                </Link>
                <Link href={`/projects/${id}/diagrams`} className="btn">
                  Diagrams
                </Link>
                <Link href={`/projects/${id}/advisor`} className="btn">
                  Advisor
                </Link>
              </div>
            </div>
          </div>

          <div className="package-split">
            <section className="panel blueprint">
              <i className="corner tl" />
              <i className="corner tr" />
              <i className="corner bl" />
              <i className="corner br" />
              <h2 style={{ fontSize: 18, marginTop: 0 }}>Architecture score</h2>
              {!dash.quality_score ? (
                <p className="muted">
                  Generate a package to see the explainable quality score.
                </p>
              ) : (
                <>
                  <p style={{ fontSize: 28, margin: "0 0 8px", fontWeight: 600 }}>
                    {dash.quality_score.overall}
                  </p>
                  <p className="muted" style={{ fontSize: 13 }}>
                    Weakest coverage state — decision support, not certification.
                  </p>
                  <div className="table-scroll" style={{ marginTop: 12 }}>
                    <table className="table">
                      <tbody>
                        {dash.quality_score.categories.map((c) => (
                          <tr key={c.id}>
                            <td>{c.label}</td>
                            <td className="muted">{c.weight}%</td>
                            <td>
                              <span className={coverageTagClass(c.coverage)}>
                                {c.coverage}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {(dash.quality_score.missing_evidence || []).length > 0 ? (
                    <>
                      <div className="card-kicker" style={{ marginTop: 16 }}>
                        Missing evidence
                      </div>
                      <ul className="tradeoff-list">
                        {dash.quality_score.missing_evidence.map((m) => (
                          <li key={m}>{m}</li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                </>
              )}
            </section>

            <section className="panel blueprint">
              <i className="corner tl" />
              <i className="corner tr" />
              <i className="corner bl" />
              <i className="corner br" />
              <h2 style={{ fontSize: 18, marginTop: 0 }}>Decision log</h2>
              {dash.decisions.length === 0 ? (
                <p className="muted">No ADRs yet — select an option first.</p>
              ) : (
                <div className="table-scroll">
                  <table className="table">
                    <tbody>
                      {dash.decisions.map((d) => (
                        <tr key={d.id}>
                          <td className="mono muted" style={{ whiteSpace: "nowrap" }}>
                            {d.id}
                          </td>
                          <td>{d.title}</td>
                          <td>
                            <span className="tag">{d.status}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>

          <div className="package-split" style={{ marginTop: 24 }}>
            <section className="panel blueprint">
              <i className="corner tl" />
              <i className="corner tr" />
              <i className="corner bl" />
              <i className="corner br" />
              <h2 style={{ fontSize: 18, marginTop: 0 }}>
                Open risks ({dash.open_risks.length})
              </h2>
              {dash.open_risks.length === 0 ? (
                <p className="muted">No medium/high risks yet.</p>
              ) : (
                <div className="table-scroll">
                  <table className="table">
                    <tbody>
                      {dash.open_risks.map((r) => (
                        <tr key={r.id}>
                          <td className="mono muted" style={{ whiteSpace: "nowrap" }}>
                            {r.id}
                          </td>
                          <td>{r.title}</td>
                          <td>
                            <span className={severityTagClass(r.severity)}>
                              {r.severity}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="panel blueprint">
              <i className="corner tl" />
              <i className="corner tr" />
              <i className="corner bl" />
              <i className="corner br" />
              <h2 style={{ fontSize: 18, marginTop: 0 }}>
                Backlog ({dash.backlog.length}) · Threats ({dash.threats.length})
              </h2>
              {dash.backlog.slice(0, 4).map((b) => (
                <div key={b.id} className="muted" style={{ fontSize: 14, marginBottom: 6 }}>
                  <strong>{b.priority}</strong> {b.title}
                </div>
              ))}
              {dash.threats.slice(0, 3).map((t) => (
                <div key={t.id} className="muted" style={{ fontSize: 14, marginBottom: 6 }}>
                  <strong>{t.stride}</strong> · {t.asset}
                </div>
              ))}
              {!dash.backlog.length && !dash.threats.length ? (
                <p className="muted">Available after package generation.</p>
              ) : null}
            </section>
          </div>
        </Reveal>
      )}
    </AppShell>
  );
}
