import { AppShell } from "@/components/AppShell";
import { Reveal } from "@/components/Reveal";
import { Stepper, type LifecycleStage } from "@/components/Stepper";
import { getProject } from "@/lib/api";
import { ExportClient } from "./ExportClient";

export default async function ExportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let reached: LifecycleStage = "export";
  try {
    const project = await getProject(id);
    if (project.lifecycle?.stage) reached = project.lifecycle.stage;
  } catch {
    /* keep */
  }

  return (
    <AppShell wide>
      <Reveal>
        <Stepper current="export" projectId={id} reachedStage={reached} />
        <h1>Export</h1>
        <p className="lede">
          Pick what goes in the zip or folder. Keep it boring.
        </p>
      </Reveal>
      <Reveal delay={0.08}>
        <ExportClient projectId={id} />
      </Reveal>
    </AppShell>
  );
}
