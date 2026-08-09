"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AmbientBackground } from "./AmbientBackground";
import { ContentScroller } from "./ContentScroller";
import { EvidenceRail } from "./EvidenceRail";
import { STEPS, type LifecycleStage } from "./Stepper";

const WORKSPACE_LINKS: {
  href: string;
  label: string;
  glyph: "grid" | "book" | "gear";
}[] = [
  { href: "/", label: "Projects", glyph: "grid" },
  { href: "/knowledge", label: "Knowledge", glyph: "book" },
  { href: "/settings", label: "Settings", glyph: "gear" },
];

function Glyph({ kind }: { kind: "grid" | "book" | "gear" | "home" }) {
  if (kind === "grid") {
    return (
      <span className="glyph glyph-grid" aria-hidden="true">
        <span />
        <span />
        <span />
        <span />
      </span>
    );
  }
  if (kind === "book") {
    return <span className="glyph glyph-book" aria-hidden="true" />;
  }
  if (kind === "home") {
    return <span className="glyph glyph-home" aria-hidden="true" />;
  }
  return <span className="glyph glyph-gear" aria-hidden="true" />;
}

export function AppShell({
  children,
  wide = false,
  projectId,
  stage,
  reachedStage,
  evidenceRail = true,
}: {
  children: React.ReactNode;
  wide?: boolean;
  /** Present once inside a project — turns on the stage rail + evidence rail. */
  projectId?: string;
  /** Stage the current page represents. */
  stage?: LifecycleStage;
  /** Furthest stage the project has actually reached — enables links through it. */
  reachedStage?: LifecycleStage;
  /** Set false on pages that already render their own, richer completeness
   *  view (e.g. Interview) — avoids showing the same numbers twice. */
  evidenceRail?: boolean;
}) {
  const pathname = usePathname();
  const order = STEPS.map((s) => s.id);
  const idx = stage ? order.indexOf(stage) : -1;
  const reachedIdx = order.indexOf(reachedStage ?? stage ?? "intake");

  return (
    <div className="af-shell">
      <AmbientBackground />
      <ContentScroller>
        <div className="workspace">
          <aside className="workspace-rail">
            <Link href="/" className="workspace-brand">
              Archavow
            </Link>

            <nav className="workspace-links">
              {WORKSPACE_LINKS.map((item) => {
                const active =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`workspace-link${active ? " is-active" : ""}`}
                    aria-current={active ? "page" : undefined}
                    aria-label={item.label}
                  >
                    <Glyph kind={item.glyph} />
                    <span className="workspace-link-label" aria-hidden="true">
                      {item.label}
                    </span>
                  </Link>
                );
              })}
            </nav>

            {projectId ? (
              <>
                <div className="workspace-rail-divider" />
                <nav className="workspace-links" aria-label="Project">
                  {(() => {
                    const dashboardHref = `/projects/${projectId}`;
                    const active = pathname === dashboardHref;
                    return (
                      <Link
                        href={dashboardHref}
                        className={`workspace-link${active ? " is-active" : ""}`}
                        aria-current={active ? "page" : undefined}
                        aria-label="Dashboard"
                      >
                        <Glyph kind="home" />
                        <span
                          className="workspace-link-label"
                          aria-hidden="true"
                        >
                          Dashboard
                        </span>
                      </Link>
                    );
                  })()}
                </nav>
              </>
            ) : null}

            {stage ? (
              <>
                <div className="workspace-rail-divider" />
                <nav className="workspace-stages" aria-label="Project stage">
                  {STEPS.map((step, i) => {
                    const state =
                      i < idx ? "done" : i === idx ? "on" : "future";
                    const linkable =
                      Boolean(projectId) &&
                      step.id !== "intake" &&
                      i <= Math.max(idx, reachedIdx);
                    const href =
                      projectId && step.id !== "intake"
                        ? `/projects/${projectId}/${step.path}`
                        : null;
                    const inner = (
                      <>
                        <span className={`workspace-stage-dot dot-${state}`}>
                          {state === "done" ? "✓" : null}
                        </span>
                        <span
                          className="workspace-link-label"
                          aria-hidden="true"
                        >
                          {step.label}
                        </span>
                      </>
                    );
                    return linkable && href ? (
                      <Link
                        key={step.id}
                        href={href}
                        className={`workspace-stage state-${state}`}
                        aria-label={step.label}
                      >
                        {inner}
                      </Link>
                    ) : (
                      <span
                        key={step.id}
                        className={`workspace-stage state-${state}`}
                        aria-label={step.label}
                      >
                        {inner}
                      </span>
                    );
                  })}
                </nav>
              </>
            ) : null}
          </aside>

          <div className="workspace-main">
            <main className={wide ? "page page-wide" : "page"}>
              {children}
            </main>
          </div>

          {projectId && evidenceRail ? (
            <EvidenceRail projectId={projectId} />
          ) : null}
        </div>
      </ContentScroller>
    </div>
  );
}
