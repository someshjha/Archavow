import { AppShell } from "@/components/AppShell";
import { Reveal } from "@/components/Reveal";
import { OnboardingForm } from "./OnboardingForm";

export default function NewProjectPage() {
  return (
    <AppShell wide stage="intake">
      <Reveal>
        <h1>Project onboarding</h1>
        <p className="lede">
          Frame the problem, constraints, and success targets. Next, the interview
          confirms requirements specific to this initiative — then options and a
          full architecture package.
        </p>
      </Reveal>
      <Reveal delay={0.08}>
        <OnboardingForm />
      </Reveal>
    </AppShell>
  );
}
