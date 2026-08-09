import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { BackLink } from "@/components/BackLink";
import { Reveal } from "@/components/Reveal";
import { type LifecycleStage } from "@/components/Stepper";
import { getPackage, getProject } from "@/lib/api";
import { AdvisorClient } from "./AdvisorClient";

export default async function AdvisorPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [pkg, project] = await Promise.all([
    getPackage(id),
    getProject(id).catch(() => null),
  ]);
  const reached: LifecycleStage = project?.lifecycle?.stage ?? "package";

  return (
    <AppShell wide projectId={id} stage="package" reachedStage={reached}>
      <Reveal>
        <BackLink>← Back to package</BackLink>
        <h1>Compare → ADR</h1>
        <p className="lede">
          Decisions leave the room as records, not chat scrollback.
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
          <AdvisorClient projectId={id} />
        </Reveal>
      )}
    </AppShell>
  );
}
