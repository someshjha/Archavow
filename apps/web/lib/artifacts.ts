/**
 * MVP artifact catalog — see docs/ARTIFACT_CATALOG.md.
 *
 * The numbers are the catalog's, not the page's. The package page browses one
 * artifact at a time via `?a=<id>`, with the index listing every section in
 * this order. Some artifacts are structured data (diagrams, ADRs, risks,
 * backlog) rather than a markdown document.
 */

export type ArtifactDoc = {
  /** Catalog number, as shown in the heading. */
  n: string;
  title: string;
  /** Key inside `package.documents`. */
  key: string;
  /** Conditional artifacts ship as light drafts (catalog: 10, 16, 18). */
  conditional?: boolean;
};

export const ARTIFACT_DOCS: ArtifactDoc[] = [
  { n: "1", title: "Architecture overview", key: "overview" },
  { n: "2", title: "Requirements", key: "requirements" },
  { n: "3", title: "Architecture options", key: "options_comparison" },
  { n: "5", title: "High-level design", key: "hld" },
  {
    n: "10",
    title: "Standards and compliance mapping",
    key: "standards_mapping",
    conditional: true,
  },
  { n: "11", title: "Implementation roadmap", key: "roadmap" },
  { n: "14", title: "Migration and deployment plan", key: "migration_plan" },
  { n: "15", title: "Operational readiness plan", key: "operational_readiness" },
  { n: "16", title: "Cost model", key: "cost_model", conditional: true },
  { n: "17", title: "Architecture review record", key: "review_record" },
  { n: "18", title: "Traceability matrix", key: "traceability", conditional: true },
];

export const ARTIFACT_DOC_KEYS: Set<string> = new Set(
  ARTIFACT_DOCS.map((d) => d.key),
);

export function artifactDoc(key: string): ArtifactDoc {
  const found = ARTIFACT_DOCS.find((d) => d.key === key);
  if (!found) throw new Error(`unknown artifact document key: ${key}`);
  return found;
}

/** Stable ids used in `/package?a=<id>` for the single-artifact browser. */
export type PackageSectionId =
  | "overview"
  | "requirements"
  | "options"
  | "diagrams"
  | "hld"
  | "adrs"
  | "risks"
  | "threats"
  | "score"
  | "standards"
  | "roadmap"
  | "arch_backlog"
  | "delivery_backlog"
  | "migration"
  | "ops"
  | "cost"
  | "review"
  | "traceability"
  | "citations";

export type PackageSectionMeta = {
  id: PackageSectionId;
  n: string;
  title: string;
  conditional?: boolean;
};

/** Full package catalog in presentation order (1–18 + citations). */
export const PACKAGE_SECTIONS: PackageSectionMeta[] = [
  { id: "overview", n: "1", title: "Architecture overview" },
  { id: "requirements", n: "2", title: "Requirements" },
  { id: "options", n: "3", title: "Architecture options" },
  { id: "diagrams", n: "4", title: "Architecture diagrams" },
  { id: "hld", n: "5", title: "High-level design" },
  { id: "adrs", n: "6", title: "ADRs" },
  { id: "risks", n: "7", title: "Risk register" },
  { id: "threats", n: "8", title: "Threat model" },
  { id: "score", n: "9", title: "Evidence checklist" },
  {
    id: "standards",
    n: "10",
    title: "Standards and compliance mapping",
    conditional: true,
  },
  { id: "roadmap", n: "11", title: "Implementation roadmap" },
  { id: "arch_backlog", n: "12", title: "Architecture backlog" },
  { id: "delivery_backlog", n: "13", title: "Delivery backlog" },
  { id: "migration", n: "14", title: "Migration and deployment plan" },
  { id: "ops", n: "15", title: "Operational readiness plan" },
  { id: "cost", n: "16", title: "Cost model", conditional: true },
  { id: "review", n: "17", title: "Architecture review record" },
  {
    id: "traceability",
    n: "18",
    title: "Traceability matrix",
    conditional: true,
  },
  { id: "citations", n: "", title: "Citations" },
];

export function packageSection(id: string): PackageSectionMeta | undefined {
  return PACKAGE_SECTIONS.find((s) => s.id === id);
}
