import { AppShell } from "@/components/AppShell";
import { Reveal } from "@/components/Reveal";
import { type LifecycleStage } from "@/components/Stepper";
import { getProject } from "@/lib/api";
import { OptionsClient } from "./OptionsClient";

export default async function OptionsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let title = "Pick an architecture option";
  let reached: LifecycleStage = "options";
  try {
    const project = await getProject(id);
    title = project.name;
    if (project.lifecycle?.stage) reached = project.lifecycle.stage;
  } catch {
    /* keep */
  }

  return (
    <AppShell wide projectId={id} stage="options" reachedStage={reached}>
      <Reveal>
        <h1>{title}</h1>
        <p className="lede">
          Pick one. Nothing else generates — no HLD, no diagrams — until you do.
        </p>
      </Reveal>
      <Reveal delay={0.08}>
        <OptionsClient projectId={id} />
      </Reveal>
    </AppShell>
  );
}
