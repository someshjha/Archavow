import { AppShell } from "@/components/AppShell";
import { Reveal } from "@/components/Reveal";
import { type LifecycleStage } from "@/components/Stepper";
import { getProject } from "@/lib/api";
import { InterviewClient } from "./InterviewClient";

export default async function InterviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let title = "Requirements interview";
  let reached: LifecycleStage = "interview";
  try {
    const project = await getProject(id);
    title = project.name;
    if (project.lifecycle?.stage) reached = project.lifecycle.stage;
  } catch {
    /* keep default */
  }

  return (
    <AppShell
      wide
      projectId={id}
      stage="interview"
      reachedStage={reached}
      evidenceRail={false}
    >
      <Reveal>
        <h1>{title}</h1>
        <p className="lede">
          Fill the gaps as they come up. Completeness stays on the right, not lost
          in chat scroll.
        </p>
      </Reveal>
      <Reveal delay={0.08}>
        <InterviewClient projectId={id} />
      </Reveal>
    </AppShell>
  );
}
