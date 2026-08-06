"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { PackageSectionId, PackageSectionMeta } from "@/lib/artifacts";
import { packageSection } from "@/lib/artifacts";

export type IndexEntry = PackageSectionMeta & { available: boolean };

function labelTitle(entry: IndexEntry) {
  return entry.n ? `${entry.n}. ${entry.title}` : entry.title;
}

export function PackageBrowser({
  entries,
  initial,
  sections,
  status,
  selectedTitle,
  aiSummary,
}: {
  entries: IndexEntry[];
  initial: PackageSectionId;
  sections: Partial<Record<PackageSectionId, React.ReactNode>>;
  status: string;
  selectedTitle: string | null;
  aiSummary?: string | null;
}) {
  const [current, setCurrent] = useState<PackageSectionId>(initial);
  const browserRef = useRef<HTMLDivElement>(null);
  const mainScrollRef = useRef<HTMLDivElement>(null);
  const indexScrollRef = useRef<HTMLElement>(null);

  const fitToViewport = useCallback(() => {
    const el = browserRef.current;
    if (!el) return;
    const top = el.getBoundingClientRect().top;
    // Sit close to the viewport bottom so the panes read tall.
    const bottomPad = 16;
    const h = Math.max(520, Math.floor(window.innerHeight - top - bottomPad));
    el.style.setProperty("--package-browser-h", `${h}px`);
  }, []);

  useLayoutEffect(() => {
    // Pull the browser under the nav first so the height calc gets most of
    // the viewport, then size the panes.
    browserRef.current?.scrollIntoView({ block: "start", behavior: "instant" });
    fitToViewport();
    const onResize = () => fitToViewport();
    window.addEventListener("resize", onResize);
    const t = window.setTimeout(fitToViewport, 120);
    return () => {
      window.removeEventListener("resize", onResize);
      window.clearTimeout(t);
    };
  }, [fitToViewport, aiSummary]);

  const select = useCallback(
    (id: PackageSectionId) => {
      const entry = entries.find((e) => e.id === id);
      if (!entry?.available) return;
      setCurrent(id);
      const url = new URL(window.location.href);
      url.searchParams.set("a", id);
      window.history.replaceState(
        null,
        "",
        `${url.pathname}?${url.searchParams.toString()}`,
      );
      if (mainScrollRef.current) {
        mainScrollRef.current.scrollTop = 0;
      }
      // Anchor the reading surface under the nav, then fill the viewport.
      const rect = browserRef.current?.getBoundingClientRect();
      if (rect && (rect.top < 8 || rect.top > 96)) {
        browserRef.current?.scrollIntoView({ block: "start", behavior: "smooth" });
        window.setTimeout(fitToViewport, 280);
      } else {
        fitToViewport();
      }
      requestAnimationFrame(() => {
        indexScrollRef.current
          ?.querySelector(".package-index-item.is-on")
          ?.scrollIntoView({ block: "nearest", inline: "nearest" });
      });
    },
    [entries, fitToViewport],
  );

  useEffect(() => {
    const onPop = () => {
      const a = new URL(window.location.href).searchParams.get("a");
      if (a && entries.some((e) => e.available && e.id === a)) {
        setCurrent(a as PackageSectionId);
        if (mainScrollRef.current) mainScrollRef.current.scrollTop = 0;
      }
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [entries]);

  const meta = packageSection(current);
  const available = entries.filter((e) => e.available);
  const idx = available.findIndex((e) => e.id === current);
  const prev = idx > 0 ? available[idx - 1] : null;
  const next = idx >= 0 && idx < available.length - 1 ? available[idx + 1] : null;

  return (
    <>
      <div className="panel blueprint package-status" style={{ marginBottom: 20 }}>
        <i className="corner tl" />
        <i className="corner tr" />
        <i className="corner bl" />
        <i className="corner br" />
        <div className="tag-row" style={{ marginBottom: 0 }}>
          <span className="tag tag-ok">{status}</span>
          {selectedTitle ? (
            <span className="tag tag-ok">{selectedTitle}</span>
          ) : null}
          {meta ? (
            <span className="tag">
              {meta.n ? `${meta.n} · ` : ""}
              {meta.title}
            </span>
          ) : null}
        </div>
        {aiSummary ? (
          <div className="probe-box" style={{ marginTop: 16 }}>
            <div className="card-kicker">In short (AI)</div>
            <p style={{ margin: "6px 0 0", fontSize: 14 }}>{aiSummary}</p>
          </div>
        ) : null}
      </div>

      <div className="package-browser" ref={browserRef}>
        <aside className="package-index panel blueprint">
          <i className="corner tl" />
          <i className="corner tr" />
          <i className="corner bl" />
          <i className="corner br" />
          <div className="package-index-head">
            <div className="card-kicker">Package index</div>
            <p className="package-index-lede muted">
              One artifact at a time — pick from the list or step with Previous /
              Next.
            </p>
          </div>
          <nav
            className="package-index-nav"
            aria-label="Package artifacts"
            ref={indexScrollRef}
            data-lenis-prevent
          >
            {entries.map((entry) => {
              if (!entry.available) {
                return (
                  <span
                    key={entry.id}
                    className="package-index-item is-missing"
                    title="Not in this package"
                  >
                    <span className="package-index-n">{entry.n || "—"}</span>
                    <span className="package-index-t">{entry.title}</span>
                  </span>
                );
              }
              const on = entry.id === current;
              return (
                <button
                  key={entry.id}
                  type="button"
                  className={`package-index-item${on ? " is-on" : ""}`}
                  aria-current={on ? "true" : undefined}
                  onClick={() => select(entry.id)}
                >
                  <span className="package-index-n">{entry.n || "·"}</span>
                  <span className="package-index-t">
                    {entry.title}
                    {entry.conditional ? (
                      <span className="tag" style={{ marginLeft: 6 }}>
                        draft
                      </span>
                    ) : null}
                  </span>
                </button>
              );
            })}
          </nav>

          <div className="package-index-pager">
            {prev ? (
              <button
                type="button"
                className="btn"
                style={{ flex: 1 }}
                title={labelTitle(prev)}
                onClick={() => select(prev.id)}
              >
                ← Prev
              </button>
            ) : (
              <span className="btn" style={{ flex: 1, opacity: 0.35 }} aria-disabled>
                ← Prev
              </span>
            )}
            {next ? (
              <button
                type="button"
                className="btn btn-primary"
                style={{ flex: 1 }}
                title={labelTitle(next)}
                onClick={() => select(next.id)}
              >
                Next →
              </button>
            ) : (
              <span className="btn" style={{ flex: 1, opacity: 0.35 }} aria-disabled>
                Next →
              </span>
            )}
          </div>
          {idx >= 0 ? (
            <p className="muted package-index-count">
              {idx + 1} of {available.length}
            </p>
          ) : null}
        </aside>

        <div className="package-browser-main">
          <div
            className="package-browser-scroll"
            ref={mainScrollRef}
            data-lenis-prevent
            tabIndex={0}
          >
            {sections[current] ?? null}
          </div>
          {prev || next ? (
            <div className="package-pager form-actions">
              {prev ? (
                <button
                  type="button"
                  className="btn"
                  onClick={() => select(prev.id)}
                >
                  ← {labelTitle(prev)}
                </button>
              ) : (
                <span />
              )}
              {next ? (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => select(next.id)}
                >
                  {labelTitle(next)} →
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </>
  );
}
