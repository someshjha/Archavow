import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { ProjectDeleteButton } from "@/components/ProjectDeleteButton";
import { Reveal } from "@/components/Reveal";
import { listProjects } from "@/lib/api";

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
            marginBottom: 64,
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

      {error ? (
        <div className="error-box" role="alert">
          {error}
          <p className="muted" style={{ marginBottom: 0, marginTop: 8 }}>
            Is the API running? Try <code>make up</code>.
          </p>
        </div>
      ) : null}

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

      <div className="card-grid">
        {projects.map((project, i) => {
          const life = project.lifecycle;
          const continueHref =
            life?.continue_path || `/projects/${project.id}/interview`;
          return (
            <Reveal key={project.id} delay={0.06 * (i + 1)}>
              <div className="card blueprint">
                <i className="corner tl" />
                <i className="corner tr" />
                <i className="corner bl" />
                <i className="corner br" />
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 8,
                    alignItems: "flex-start",
                  }}
                >
                  <div className="card-title">{project.name}</div>
                  {life ? (
                    <span className="tag tag-ok">{life.label}</span>
                  ) : null}
                </div>
                <p className="muted" style={{ margin: "0 0 8px" }}>
                  {project.description || project.stack_tags.join(" · ") || "—"}
                </p>
                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    flexWrap: "wrap",
                    marginBottom: 12,
                  }}
                >
                  {project.stack_tags.map((tag) => (
                    <span key={tag} className="tag">
                      {tag}
                    </span>
                  ))}
                </div>
                {life ? (
                  <p className="muted" style={{ fontSize: 13, margin: "0 0 12px" }}>
                    {[
                      life.milestones.interview_ready && "Interview ready",
                      life.milestones.options_ready && "Options",
                      life.milestones.option_selected && "Selected",
                      life.milestones.package_ready && "Package",
                      life.milestones.export_done && "Exported",
                    ]
                      .filter(Boolean)
                      .join(" · ") || "Onboarding complete"}
                  </p>
                ) : null}
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
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
                  <Link
                    href={`/projects/${project.id}/interview`}
                    className="btn"
                    style={{ padding: "6px 14px" }}
                  >
                    Interview
                  </Link>
                  <Link
                    href={`/projects/${project.id}/options`}
                    className="btn"
                    style={{ padding: "6px 14px" }}
                  >
                    Options
                  </Link>
                  <ProjectDeleteButton
                    projectId={project.id}
                    projectName={project.name}
                  />
                </div>
              </div>
            </Reveal>
          );
        })}
      </div>
    </AppShell>
  );
}
