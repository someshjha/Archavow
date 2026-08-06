import { AppShell } from "@/components/AppShell";
import { Reveal } from "@/components/Reveal";
import { KnowledgeClient } from "./KnowledgeClient";

export default function KnowledgePage() {
  return (
    <AppShell>
      <Reveal>
        <h1>Knowledge</h1>
        <p className="lede">
          Drop org standards here. Generation cites them when it can.
        </p>
      </Reveal>
      <Reveal delay={0.08}>
        <KnowledgeClient />
      </Reveal>
    </AppShell>
  );
}
