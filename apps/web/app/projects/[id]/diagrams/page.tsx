import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { BackLink } from "@/components/BackLink";
import { Reveal } from "@/components/Reveal";
import { type LifecycleStage } from "@/components/Stepper";
import { getPackage, getProject } from "@/lib/api";
import { DiagramsClient } from "./DiagramsClient";

type PackageDiagrams = {
  mermaid: string;
  mermaid_container?: string;
  mermaid_sequence?: string;
  documents?: Record<string, string>;
};

export default async function DiagramsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [pkgRaw, project] = await Promise.all([
    getPackage(id),
    getProject(id).catch(() => null),
  ]);
  const pkg = pkgRaw as PackageDiagrams | null;
  const reached: LifecycleStage = project?.lifecycle?.stage ?? "package";
  const docs = pkg?.documents || {};

  return (
    <AppShell wide projectId={id} stage="package" reachedStage={reached}>
      <Reveal>
        <BackLink>← Back to package</BackLink>
        <h1>Architecture diagrams</h1>
        <p className="lede">
          C4 levels 1–3, the key interaction sequence, and a labeled data flow
          from the selected option.
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
          <DiagramsClient
            sources={{
              context: pkg.mermaid,
              container: pkg.mermaid_container,
              component: docs.diagram_component,
              sequence: pkg.mermaid_sequence,
              dataflow: docs.diagram_dataflow,
            }}
          />
        </Reveal>
      )}
    </AppShell>
  );
}
