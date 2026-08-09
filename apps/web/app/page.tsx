import Link from "next/link";
import { ApiUnavailable } from "@/components/ApiUnavailable";
import { AppShell } from "@/components/AppShell";
import { ProjectDeleteButton } from "@/components/ProjectDeleteButton";
import { Reveal } from "@/components/Reveal";
import { listProjects, type Project } from "@/lib/api";

const MILESTONE_KEYS = [
  "intake_done",
  "interview_started",
  "interview_ready",
  "options_ready",
  "option_selected",
  "package_ready",
  "export_done",
] as const;

function progressOf(project: Project): { done: number; total: number } {
  const milestones = project.lifecycle?.milestones;
  if (!milestones) return { done: 0, total: MILESTONE_KEYS.length };
  const done = MILESTONE_KEYS.filter((k) => milestones[k]).length;
  return { done, total: MILESTONE_KEYS.length };
}

export default async function ProjectsPage() {
  let error: string | null = null;
  let projects: Awaited<ReturnType<typeof listProjects>> = [];

  try {
    projects = await listProjects();
  } catch (err) {
    error = err instanceof Error ? err.message : "Failed to load projects";
  }

  return (
    <AppShell wide>
      <Reveal>
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 32,
            flexWrap: "wrap",
            marginBottom: 48,
          }}
        >
          <div style={{ flex: 1 }}>
            <h1>Projects</h1>
            <p className="lede" style={{ marginBottom: 0 }}>
              Build better systems before writing code.
            </p>
          </div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", flexShrink: 0 }}>
            <Link href="/projects/new" className="btn btn-primary blueprint">
              <i className="corner tl" />
              <i className="corner tr" />
              <i className="corner bl" />
              <i className="corner br" />
              + Start onboarding
            </Link>
            <Link href="/settings" className="btn">
              AI settings
            </Link>
          </div>
        </div>
      </Reveal>

      {error ? <ApiUnavailable detail={error} /> : null}

      {!error && projects.length === 0 ? (
        <Reveal delay={0.08}>
          <div className="panel blueprint">
            <i className="corner tl" />
            <i className="corner tr" />
            <i className="corner bl" />
            <i className="corner br" />
            <h2>No projects yet</h2>
            <p className="muted" style={{ marginBottom: 0 }}>
              Create a project to start onboarding → interview → options → package.
            </p>
          </div>
        </Reveal>
      ) : null}

      {projects.length > 0 ? (
        <Reveal delay={0.06}>
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Stage</th>
                  <th>Progress</th>
                  <th aria-hidden="true" />
                </tr>
              </thead>
              <tbody>
                {projects.map((project) => {
                  const life = project.lifecycle;
                  const continueHref =
                    life?.continue_path || `/projects/${project.id}/interview`;
                  const { done, total } = progressOf(project);
                  const pct = total ? Math.round((done / total) * 100) : 0;
                  return (
                    <tr key={project.id}>
                      <td className="table-name">
                        <Link href={`/projects/${project.id}`}>
                          {project.name}
                        </Link>
                        {project.description ? (
                          <p
                            className="muted"
                            style={{ margin: "4px 0 0", fontWeight: 400, fontSize: 13 }}
                          >
                            {project.description}
                          </p>
                        ) : null}
                        {project.stack_tags.length > 0 ? (
                          <div className="tag-row" style={{ marginTop: 6 }}>
                            {project.stack_tags.slice(0, 4).map((tag) => (
                              <span key={tag} className="tag">
                                {tag}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </td>
                      <td>
                        {life ? (
                          <span className="tag tag-ok">{life.label}</span>
                        ) : (
                          <span className="muted">—</span>
                        )}
                      </td>
                      <td>
                        <span className="table-bar">
                          <span className="bar">
                            <span style={{ width: `${pct}%` }} />
                          </span>
                          <b>
                            {done}/{total}
                          </b>
                        </span>
                      </td>
                      <td>
                        <div
                          style={{
                            display: "flex",
                            gap: 8,
                            flexWrap: "wrap",
                            justifyContent: "flex-end",
                          }}
                        >
                          <Link
                            href={continueHref}
                            className="btn btn-primary"
                            style={{ padding: "6px 14px" }}
                          >
                            Continue
                          </Link>
                          <Link
                            href={`/projects/${project.id}`}
                            className="btn"
                            style={{ padding: "6px 14px" }}
                          >
                            Dashboard
                          </Link>
                          <ProjectDeleteButton
                            projectId={project.id}
                            projectName={project.name}
                          />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Reveal>
      ) : null}
    </AppShell>
  );
}
