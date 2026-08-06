"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState, useTransition } from "react";
import { CancelLink } from "@/components/Stepper";
import { revalidateProjects } from "@/app/actions";

const EMPTY_FORM = {
  name: "",
  business_objective: "",
  problem_statement: "",
  requirements: "",
  preferred_cloud: "",
  scale_availability: "",
  tech_constraints: "",
};

const DEMO_FORM = {
  name: "Claims Intake & Automated Adjudication",
  business_objective:
    "Cut the time from claim submission to decision from five days to under ten minutes for straightforward claims, without increasing leakage.",
  problem_statement:
    "Every claim is adjudicated by hand from email and PDF attachments. Adjusters spend most of their day on simple, low-value claims, complex claims wait behind them, and there is no consistent record of why a claim was approved or declined.",
  requirements: [
    "Claimants must submit a claim online with supporting documents and photos.",
    "The system must validate the policy is active and covers the claimed loss before adjudication.",
    "Straightforward claims must be adjudicated automatically against the published rules.",
    "Claims above 5,000 or with missing evidence must be routed to a human adjuster with the reason.",
    "Suspicious or duplicate claims must be flagged and held for investigation.",
    "Approved claims must trigger a payment to the claimant's verified account exactly once.",
    "Claimants must be able to see the current status of their claim without calling support.",
    "The system must integrate with the existing policy administration system as the system of record.",
    "Every decision must retain an immutable audit trail for seven years for regulatory review.",
    "Operations managers must see claim volume, cycle time, and exception rates daily.",
  ].join("\n"),
  preferred_cloud: "Azure",
  scale_availability:
    "2k claims/hour peak · 99.9% availability · RTO 15m · RPO 1m · decision under 10s",
  tech_constraints: "Java 21, Spring Boot, Kafka, AKS, Postgres, Entra ID",
};

/** One requirement per line — order is preserved because story traceability
 *  references (R-001, R-002…) are positional. */
function parseRequirements(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.replace(/^\s*(?:[-*•]|\d+[.)])\s*/, "").trim())
    .filter(Boolean);
}

export function OnboardingForm() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);

  function set<K extends keyof typeof form>(key: K, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function deriveStackTags(cloud: string, constraints: string): string[] {
    const tags = new Set<string>();
    const blob = `${cloud} ${constraints}`.toLowerCase();
    const rules: [RegExp, string][] = [
      [/\bazure\b/, "azure"],
      [/\baws\b/, "aws"],
      [/\bgcp\b|\bgoogle\s*cloud\b/, "gcp"],
      [/\bon[- ]?prem\b|\bonprem\b|\bprivate\s+cloud\b/, "on-premises"],
      [/\bkafka\b/, "kafka"],
      [/\bspring(?:\s|-)?boot\b|\bspring\b/, "spring-boot"],
      [/\baks\b|\bkubernetes\b|\bk8s\b/, "kubernetes"],
      [/\bpostgres(?:ql)?\b/, "postgres"],
      [/\bpython\b/, "python"],
      [/\bjava\b/, "java"],
      [/\bcognito\b|\bentra\b|\bokta\b|\bauth0\b|\boidc\b/, "identity"],
    ];
    for (const [re, tag] of rules) {
      if (re.test(blob)) tags.add(tag);
    }
    return [...tags];
  }

  const derivedTags = useMemo(
    () => deriveStackTags(form.preferred_cloud, form.tech_constraints),
    [form.preferred_cloud, form.tech_constraints],
  );

  const requirements = useMemo(
    () => parseRequirements(form.requirements),
    [form.requirements],
  );

  const completenessHints = useMemo(() => {
    const hints: string[] = [];
    if (!form.business_objective.trim()) hints.push("Add a business objective");
    if (!form.problem_statement.trim()) hints.push("Describe the problem to solve");
    if (requirements.length === 0) hints.push("List what the system must do");
    if (!form.preferred_cloud) hints.push("Pick a landing zone / cloud");
    if (!form.scale_availability.trim()) hints.push("Note scale or availability targets");
    if (!form.tech_constraints.trim()) hints.push("List hard tech constraints");
    return hints;
  }, [form, requirements.length]);

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    startTransition(async () => {
      try {
        const res = await fetch("/api/backend/projects", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...form,
            requirements,
            stack_tags: deriveStackTags(form.preferred_cloud, form.tech_constraints),
          }),
        });
        if (!res.ok) throw new Error(await res.text());
        const body = await res.json();
        const id = body.data.id as string;
        await revalidateProjects();
        router.push(`/projects/${id}/interview`);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Create failed");
      }
    });
  }

  return (
    <form onSubmit={onSubmit}>
      {error ? (
        <div className="error-box" role="alert">
          {error}
        </div>
      ) : null}

      <div className="intake-layout">
        <div className="onboarding-form">
          <section className="onboarding-section panel blueprint">
            <i className="corner tl" />
            <i className="corner tr" />
            <i className="corner bl" />
            <i className="corner br" />
            <div className="card-kicker">1 · Identity</div>
            <h2 className="onboarding-section-title">Name the initiative</h2>
            <p className="muted onboarding-help">
              Use the name stakeholders already recognize — it becomes the title
              on every diagram and export.
            </p>
            <div className="field">
              <label htmlFor="name">Project name</label>
              <input
                id="name"
                required
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                placeholder="e.g. Payments event platform"
              />
            </div>
          </section>

          <section className="onboarding-section panel blueprint">
            <i className="corner tl" />
            <i className="corner tr" />
            <i className="corner bl" />
            <i className="corner br" />
            <div className="card-kicker">2 · Problem framing</div>
            <h2 className="onboarding-section-title">What are we solving?</h2>
            <p className="muted onboarding-help">
              Be specific about actors, pain, and success. The interview will
              confirm requirements from this framing — not a generic checklist.
            </p>
            <div className="field">
              <label htmlFor="obj">Business objective</label>
              <textarea
                id="obj"
                rows={3}
                value={form.business_objective}
                onChange={(e) => set("business_objective", e.target.value)}
                placeholder="What outcome should this system produce for the business?"
              />
            </div>
            <div className="field">
              <label htmlFor="prob">Problem statement</label>
              <textarea
                id="prob"
                rows={4}
                value={form.problem_statement}
                onChange={(e) => set("problem_statement", e.target.value)}
                placeholder="What is broken or missing today? Who feels the pain? What fails at peak or under failure?"
              />
            </div>
          </section>

          <section className="onboarding-section panel blueprint">
            <i className="corner tl" />
            <i className="corner tr" />
            <i className="corner bl" />
            <i className="corner br" />
            <div className="card-kicker">3 · Requirements</div>
            <h2 className="onboarding-section-title">What must it do?</h2>
            <p className="muted onboarding-help">
              One requirement per line, in the words the business uses. These
              become epics and user stories after you pick an option, and every
              story cites the line it came from.
            </p>
            <div className="field">
              <label htmlFor="reqs">Requirements</label>
              <textarea
                id="reqs"
                rows={8}
                value={form.requirements}
                onChange={(e) => set("requirements", e.target.value)}
                placeholder={
                  "Claimants must submit a claim online with supporting documents.\nStraightforward claims must be decided automatically.\nClaims above 5,000 must be reviewed by a human."
                }
              />
              <p className="field-hint">
                {requirements.length === 0 ? (
                  "Nothing captured yet — the interview will have to ask for all of it."
                ) : (
                  <>
                    <strong>{requirements.length}</strong>{" "}
                    {requirements.length === 1 ? "requirement" : "requirements"}{" "}
                    captured · traced as{" "}
                    <span className="mono">R-001</span>
                    {requirements.length > 1 ? (
                      <>
                        {"–"}
                        <span className="mono">
                          {`R-${String(requirements.length).padStart(3, "0")}`}
                        </span>
                      </>
                    ) : null}
                  </>
                )}
              </p>
            </div>
          </section>

          <section className="onboarding-section panel blueprint">
            <i className="corner tl" />
            <i className="corner tr" />
            <i className="corner bl" />
            <i className="corner br" />
            <div className="card-kicker">4 · Constraints</div>
            <h2 className="onboarding-section-title">Boundaries we must respect</h2>
            <p className="muted onboarding-help">
              Cloud, scale, and non-negotiable tech shape the options. Leave a
              field blank only if it is truly undecided — the interview will ask.
            </p>
            <div className="form-row">
              <div className="field">
                <label htmlFor="cloud">Preferred cloud / landing zone</label>
                <select
                  id="cloud"
                  value={form.preferred_cloud}
                  onChange={(e) => set("preferred_cloud", e.target.value)}
                >
                  <option value="">Select…</option>
                  <option value="Azure">Azure</option>
                  <option value="AWS">AWS</option>
                  <option value="GCP">GCP</option>
                  <option value="On-prem">On-prem / private</option>
                  <option value="Other">Other / undecided</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="scale">Scale, availability, DR targets</label>
                <input
                  id="scale"
                  value={form.scale_availability}
                  onChange={(e) => set("scale_availability", e.target.value)}
                  placeholder="e.g. 5k events/sec · 99.9% · RTO 15m · RPO 1m"
                />
              </div>
            </div>
            <div className="field">
              <label htmlFor="constraints">Tech constraints</label>
              <textarea
                id="constraints"
                rows={3}
                value={form.tech_constraints}
                onChange={(e) => set("tech_constraints", e.target.value)}
                placeholder="Languages, platforms, brokers, identity, data stores you must use (or must avoid)"
              />
            </div>
            {derivedTags.length > 0 ? (
              <div className="tag-row" style={{ marginTop: 8 }}>
                {derivedTags.map((t) => (
                  <span key={t} className="tag">
                    {t}
                  </span>
                ))}
              </div>
            ) : null}
          </section>

          <div className="form-actions">
            <CancelLink />
            <button
              type="button"
              className="btn"
              disabled={pending}
              onClick={() => setForm(DEMO_FORM)}
            >
              Load demo scenario
            </button>
            <button type="submit" className="btn btn-primary" disabled={pending}>
              Save &amp; start interview
            </button>
          </div>
        </div>

        <aside className="panel blueprint onboarding-aside">
          <i className="corner tl" />
          <i className="corner tr" />
          <i className="corner bl" />
          <i className="corner br" />
          <div className="card-kicker">Onboarding path</div>
          <ol className="onboarding-steps">
            <li>
              <strong>Frame the problem</strong> — objective, pain, and what it must do
            </li>
            <li>
              <strong>Confirm requirements</strong> — the interview asks only what is missing
            </li>
            <li>
              <strong>Compare options</strong> — distinct solution approaches
            </li>
            <li>
              <strong>Package &amp; export</strong> — diagrams, ADRs, risks, epics and
              user stories
            </li>
          </ol>
          <div className="card-kicker" style={{ marginTop: 20 }}>
            Still thin
          </div>
          {completenessHints.length === 0 ? (
            <p className="muted" style={{ marginBottom: 0 }}>
              Enough to start a useful interview.
            </p>
          ) : (
            <ul className="onboarding-gaps">
              {completenessHints.map((h) => (
                <li key={h}>{h}</li>
              ))}
            </ul>
          )}
          <p className="muted onboarding-note">
            Load demo fills in the sample insurance claims scenario — ten
            requirements, Azure, and a Java stack.
          </p>
        </aside>
      </div>
    </form>
  );
}

/** @deprecated Use OnboardingForm */
export const IntakeForm = OnboardingForm;
