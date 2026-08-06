import Link from "next/link";
import type { ReactNode } from "react";
import { AppShell } from "@/components/AppShell";
import {
  ArchitectureBacklog,
  type BacklogItem,
} from "@/components/ArchitectureBacklog";
import {
  ArtifactDocPanel,
  ArtifactHeading,
  ArtifactPanel,
} from "@/components/ArtifactPanel";
import { DeliveryBacklog, type Epic } from "@/components/DeliveryBacklog";
import { MermaidBlock } from "@/components/MermaidBlock";
import { MarkdownBody } from "@/components/MarkdownBody";
import {
  PackageBrowser,
  type IndexEntry,
} from "@/components/PackageIndex";
import { Reveal } from "@/components/Reveal";
import { Stepper, type LifecycleStage } from "@/components/Stepper";
import { getOptions, getPackage, getProject } from "@/lib/api";
import {
  ARTIFACT_DOC_KEYS,
  PACKAGE_SECTIONS,
  type PackageSectionId,
} from "@/lib/artifacts";

type Adr = {
  id: string;
  title: string;
  status: string;
  context: string;
  decision: string;
  consequences: string[];
  rationale?: string;
  alternatives?: string[];
  owner?: string | null;
};

type Risk = {
  id: string;
  title: string;
  category: string;
  severity: string;
  likelihood: string;
  impact: string;
  mitigation: string;
  residual_risk?: string;
  owner: string | null;
  target_date?: string | null;
};

type Citation = {
  document_id: string;
  chunk_id: string;
  title: string;
  source_class: string;
  citation: string;
  excerpt: string;
  score: number;
};

type Pkg = {
  status: string;
  option_id: string;
  hld_markdown: string;
  mermaid: string;
  mermaid_container?: string;
  mermaid_sequence?: string;
  adrs: Adr[];
  risks: Risk[];
  citations: Citation[];
  quality_score?: {
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
    method?: string;
    confidence?: string;
  };
  backlog?: BacklogItem[];
  epics?: Epic[];
  threats?: {
    id: string;
    stride: string;
    asset: string;
    boundary: string;
    threat: string;
    mitigation: string;
  }[];
  documents?: Record<string, string>;
  retrieval_status: string;
  ai_summary?: string | null;
  ai_assist?: { status: string; detail?: string | null };
  provenance: Record<string, unknown>;
  selectedTitle: string | null;
};

async function loadPackage(projectId: string): Promise<Pkg | null> {
  const [pkgRaw, opts] = await Promise.all([
    getPackage(projectId),
    getOptions(projectId).catch(() => null),
  ]);
  if (!pkgRaw) return null;
  const pkg = pkgRaw as Omit<Pkg, "selectedTitle">;
  let selectedTitle: string | null = null;
  if (opts) {
    const match =
      opts.options.find((o) => o.id === pkg.option_id) ||
      opts.options.find((o) => o.selected);
    selectedTitle = match?.title ?? null;
  }
  return { ...pkg, selectedTitle };
}

function hasDoc(docs: Record<string, string>, key: string) {
  return Boolean((docs[key] || "").trim());
}

function availableSections(pkg: Pkg): IndexEntry[] {
  const docs = pkg.documents || {};
  const present: Record<PackageSectionId, boolean> = {
    overview: hasDoc(docs, "overview"),
    requirements: hasDoc(docs, "requirements"),
    options: hasDoc(docs, "options_comparison"),
    diagrams: Boolean(pkg.mermaid?.trim()),
    hld: hasDoc(docs, "hld") || Boolean(pkg.hld_markdown?.trim()),
    adrs: true,
    risks: true,
    threats: true,
    score: true,
    standards: hasDoc(docs, "standards_mapping"),
    roadmap: hasDoc(docs, "roadmap"),
    arch_backlog: true,
    delivery_backlog: (pkg.epics || []).length > 0,
    migration: hasDoc(docs, "migration_plan"),
    ops: hasDoc(docs, "operational_readiness"),
    cost: hasDoc(docs, "cost_model"),
    review: hasDoc(docs, "review_record"),
    traceability: hasDoc(docs, "traceability"),
    citations: (pkg.citations || []).length > 0,
  };
  return PACKAGE_SECTIONS.map((s) => ({
    ...s,
    available: present[s.id],
  }));
}

function resolveCurrent(
  requested: string | undefined,
  entries: IndexEntry[],
): PackageSectionId {
  const available = entries.filter((e) => e.available);
  if (requested && available.some((e) => e.id === requested)) {
    return requested as PackageSectionId;
  }
  return (available[0]?.id || "overview") as PackageSectionId;
}

export default async function PackagePage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ a?: string }>;
}) {
  const { id } = await params;
  const { a: requested } = await searchParams;
  const [pkg, project] = await Promise.all([
    loadPackage(id),
    getProject(id).catch(() => null),
  ]);
  const reached: LifecycleStage = project?.lifecycle?.stage ?? "package";
  const docs = pkg?.documents || {};
  const docKeys = Object.keys(docs).filter(
    (k) => ARTIFACT_DOC_KEYS.has(k) && (docs[k] || "").trim(),
  );
  const workflow = String(pkg?.provenance?.workflow_version || "");
  const needsRegen =
    Boolean(pkg) && (docKeys.length === 0 || !/v[78]/.test(workflow));

  const entries = pkg ? availableSections(pkg) : [];
  const current = resolveCurrent(requested, entries);
  const sections: Partial<Record<PackageSectionId, ReactNode>> = {};
  if (pkg) {
    for (const entry of entries) {
      if (!entry.available) continue;
      sections[entry.id] = renderSection(entry.id, pkg, docs);
    }
  }

  return (
    <AppShell wide>
      <Reveal>
        <Stepper current="package" projectId={id} reachedStage={reached} />
        <h1>Architecture package</h1>
        <p className="lede">
          Browse the MVP catalog one artifact at a time. Use the index to jump,
          or step Previous / Next — export still ships the full set.
        </p>
      </Reveal>

      {!pkg ? (
        <div className="error-box" role="alert">
          No package yet. Select an option first.
          <div className="form-actions">
            <Link href={`/projects/${id}/options`} className="btn btn-primary">
              Choose option
            </Link>
          </div>
        </div>
      ) : (
        <Reveal delay={0.08}>
          {needsRegen ? (
            <div className="error-box" role="status" style={{ marginBottom: 16 }}>
              This package was built before the MVP artifact catalog. Open{" "}
              <Link href={`/projects/${id}/options`}>Options</Link>, select the
              option again (or re-open the selected one) so the package
              regenerates with overview, requirements, roadmap, and the rest.
            </div>
          ) : null}

          <PackageBrowser
            entries={entries}
            initial={current}
            sections={sections}
            status={pkg.status}
            selectedTitle={pkg.selectedTitle}
            aiSummary={pkg.ai_summary}
          />

          <div className="form-actions" style={{ marginTop: 28 }}>
            <Link href={`/projects/${id}`} className="btn">
              Dashboard
            </Link>
            <Link href={`/projects/${id}/options`} className="btn btn-primary">
              {needsRegen ? "Regenerate package →" : "Change option"}
            </Link>
            <Link href={`/projects/${id}/diagrams`} className="btn">
              View diagrams →
            </Link>
            <Link href={`/projects/${id}/advisor`} className="btn">
              Advisor
            </Link>
            <Link href={`/projects/${id}/export`} className="btn btn-primary">
              Export…
            </Link>
            <Link href="/" className="btn">
              Projects
            </Link>
          </div>
        </Reveal>
      )}
    </AppShell>
  );
}

function renderSection(
  id: PackageSectionId,
  pkg: Pkg,
  docs: Record<string, string>,
) {
  switch (id) {
    case "overview":
      return <ArtifactDocPanel docKey="overview" docs={docs} />;
    case "requirements":
      return <ArtifactDocPanel docKey="requirements" docs={docs} />;
    case "options":
      return <ArtifactDocPanel docKey="options_comparison" docs={docs} />;
    case "diagrams":
      return (
        <ArtifactPanel n="4" title="Architecture diagrams">
          <p className="muted" style={{ fontSize: 14 }}>
            C4 levels 1–3, the key interaction sequence, and a labeled data
            flow showing who sends what and where it lands.
          </p>
          <MermaidBlock title="Level 1 — System context" source={pkg.mermaid} />
          {pkg.mermaid_container ? (
            <MermaidBlock
              title="Level 2 — Containers"
              source={pkg.mermaid_container}
            />
          ) : null}
          {docs.diagram_component ? (
            <MermaidBlock
              title="Level 3 — Components"
              source={docs.diagram_component}
            />
          ) : null}
          {pkg.mermaid_sequence ? (
            <MermaidBlock
              title="Key interaction sequence"
              source={pkg.mermaid_sequence}
            />
          ) : null}
          {docs.diagram_dataflow ? (
            <MermaidBlock
              title="Data flow — who sends what, where it lands"
              source={docs.diagram_dataflow}
            />
          ) : null}
        </ArtifactPanel>
      );
    case "hld":
      if (docs.hld?.trim()) {
        return <ArtifactDocPanel docKey="hld" docs={docs} />;
      }
      return (
        <ArtifactPanel n="5" title="High-level design">
          <MarkdownBody>{pkg.hld_markdown}</MarkdownBody>
        </ArtifactPanel>
      );
    case "adrs":
      return (
        <ArtifactPanel n="6" title="ADRs">
          {(pkg.adrs || []).length === 0 ? (
            <p className="muted">No ADRs yet.</p>
          ) : (
            (pkg.adrs || []).map((adr) => (
              <article key={adr.id} className="adr-block">
                <div className="tag-row" style={{ marginBottom: 6 }}>
                  <span className="tag tag-ok">{adr.id}</span>
                  <span className="tag">{adr.status}</span>
                  {adr.owner ? <span className="tag">{adr.owner}</span> : null}
                </div>
                <h3 style={{ fontSize: 16, margin: "0 0 8px" }}>{adr.title}</h3>
                <div className="card-kicker">Context</div>
                <p style={{ fontSize: 14, margin: "4px 0 10px" }}>{adr.context}</p>
                <div className="card-kicker">Decision</div>
                <p style={{ fontSize: 14, margin: "4px 0 10px" }}>{adr.decision}</p>
                {adr.rationale ? (
                  <>
                    <div className="card-kicker">Rationale</div>
                    <p style={{ fontSize: 14, margin: "4px 0 10px" }}>
                      {adr.rationale}
                    </p>
                  </>
                ) : null}
                {(adr.alternatives || []).length > 0 ? (
                  <>
                    <div className="card-kicker">Alternatives</div>
                    <ul className="tradeoff-list" style={{ marginTop: 4 }}>
                      {(adr.alternatives || []).map((alt) => (
                        <li key={alt}>{alt}</li>
                      ))}
                    </ul>
                  </>
                ) : null}
                <div className="card-kicker">Consequences</div>
                <ul className="tradeoff-list" style={{ marginTop: 4 }}>
                  {(adr.consequences || []).map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </article>
            ))
          )}
        </ArtifactPanel>
      );
    case "risks":
      return (
        <ArtifactPanel n="7" title="Risk register">
          {(pkg.risks || []).length === 0 ? (
            <p className="muted">No risks yet.</p>
          ) : (
            (pkg.risks || []).map((risk) => (
              <article key={risk.id} className="risk-block">
                <div className="tag-row" style={{ marginBottom: 6 }}>
                  <span className="tag">{risk.id}</span>
                  <span
                    className={`tag ${risk.severity === "high" ? "tag-bad" : ""}`}
                  >
                    {risk.severity}
                  </span>
                  <span className="tag">{risk.category}</span>
                </div>
                <h3 style={{ fontSize: 16, margin: "0 0 8px" }}>{risk.title}</h3>
                <div className="card-kicker">Impact</div>
                <p style={{ fontSize: 14, margin: "4px 0 10px" }}>{risk.impact}</p>
                <div className="card-kicker">Mitigation</div>
                <p style={{ fontSize: 14, margin: "4px 0 0" }}>{risk.mitigation}</p>
                {risk.residual_risk ? (
                  <>
                    <div className="card-kicker" style={{ marginTop: 10 }}>
                      Residual risk
                    </div>
                    <p style={{ fontSize: 14, margin: "4px 0 0" }}>
                      {risk.residual_risk}
                    </p>
                  </>
                ) : null}
              </article>
            ))
          )}
        </ArtifactPanel>
      );
    case "threats":
      return (
        <ArtifactPanel n="8" title="Threat model">
          {(pkg.threats || []).length === 0 ? (
            <p className="muted">No threats sketched.</p>
          ) : (
            (pkg.threats || []).map((t) => (
              <article key={t.id} className="risk-block">
                <div className="tag-row" style={{ marginBottom: 6 }}>
                  <span className="tag">{t.id}</span>
                  <span className="tag tag-ok">{t.stride}</span>
                </div>
                <h3 style={{ fontSize: 15, margin: "0 0 6px" }}>{t.asset}</h3>
                <p style={{ fontSize: 14, margin: "0 0 8px" }}>{t.threat}</p>
                <p className="muted" style={{ fontSize: 13, margin: 0 }}>
                  Mitigation: {t.mitigation}
                </p>
              </article>
            ))
          )}
        </ArtifactPanel>
      );
    case "score":
      return (
        <ArtifactPanel n="9" title="Evidence checklist">
          {!pkg.quality_score ? (
            <p className="muted">Not scored yet.</p>
          ) : (
            <>
              <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>
                Coverage states from intake keyword presence — not a certification.
                Method: {pkg.quality_score.method || "intake_keyword_presence"}
                {pkg.quality_score.confidence
                  ? ` · confidence ${pkg.quality_score.confidence}`
                  : ""}
                .
              </p>
              <p className="score-readout">
                <strong>{pkg.quality_score.overall}</strong>{" "}
                <span className="tag">{pkg.quality_score.label}</span>
              </p>
              {(pkg.quality_score.categories || []).map((c) => (
                <div key={c.id} className="score-row">
                  <span className="score-label">{c.label}</span>
                  <span className="score-bar score-bar-flat">
                    <span className={`tag coverage-${c.coverage}`}>{c.coverage}</span>
                  </span>
                  <span className="score-value mono muted">{c.weight}%</span>
                </div>
              ))}
              {(pkg.quality_score.missing_evidence || []).length > 0 ? (
                <>
                  <div className="card-kicker" style={{ marginTop: 16 }}>
                    Missing evidence
                  </div>
                  <ul className="tradeoff-list">
                    {pkg.quality_score.missing_evidence.map((m) => (
                      <li key={m}>{m}</li>
                    ))}
                  </ul>
                </>
              ) : null}
              {(pkg.quality_score.blockers || []).length > 0 ? (
                <>
                  <div className="card-kicker" style={{ marginTop: 16 }}>
                    Blockers
                  </div>
                  <ul className="tradeoff-list">
                    {pkg.quality_score.blockers.map((b) => (
                      <li key={b}>{b}</li>
                    ))}
                  </ul>
                </>
              ) : null}
            </>
          )}
        </ArtifactPanel>
      );
    case "standards":
      return <ArtifactDocPanel docKey="standards_mapping" docs={docs} />;
    case "roadmap":
      return <ArtifactDocPanel docKey="roadmap" docs={docs} />;
    case "arch_backlog":
      return <ArchitectureBacklog items={pkg.backlog || []} />;
    case "delivery_backlog":
      return <DeliveryBacklog epics={pkg.epics || []} />;
    case "migration":
      return <ArtifactDocPanel docKey="migration_plan" docs={docs} />;
    case "ops":
      return <ArtifactDocPanel docKey="operational_readiness" docs={docs} />;
    case "cost":
      return <ArtifactDocPanel docKey="cost_model" docs={docs} />;
    case "review":
      return <ArtifactDocPanel docKey="review_record" docs={docs} />;
    case "traceability":
      return <ArtifactDocPanel docKey="traceability" docs={docs} />;
    case "citations":
      return (
        <section className="panel blueprint artifact">
          <i className="corner tl" />
          <i className="corner tr" />
          <i className="corner bl" />
          <i className="corner br" />
          <ArtifactHeading
            n=""
            title={`Citations (${(pkg.citations || []).length})`}
          />
          {(pkg.citations || []).length === 0 ? (
            <p className="muted">
              No knowledge citations — upload standards under Knowledge and
              re-generate the package.
            </p>
          ) : (
            <div className="cite-list">
              {(pkg.citations || []).map((c) => (
                <div key={c.chunk_id} className="probe-box">
                  <strong>{c.citation}</strong>{" "}
                  <span className="tag">{c.source_class}</span>{" "}
                  <span className="muted">score {c.score}</span>
                  <p style={{ margin: "8px 0 0", fontSize: 14 }}>{c.excerpt}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      );
    default:
      return null;
  }
}
