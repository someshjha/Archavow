import type { ReactNode } from "react";

export type AcceptanceCriterion = {
  id: string;
  given: string;
  when: string;
  then: string;
};

export type Story = {
  id: string;
  type: "business" | "enabler" | string;
  title: string;
  actor?: string;
  need?: string;
  priority?: string;
  origin?: string;
  requirement_refs?: string[];
  requirement_texts?: string[];
  acceptance_criteria?: AcceptanceCriterion[];
  nfr_checks?: string[];
  dependencies?: string[];
};

export type Epic = {
  id: string;
  title: string;
  need?: string;
  business_outcome?: string;
  priority?: string;
  origin?: string;
  requirement_refs?: string[];
  stories?: Story[];
};

function Chip({
  children,
  tone,
}: {
  children: ReactNode;
  tone?: "trace" | "enabler" | "priority" | "baseline";
}) {
  return <span className={`chip${tone ? ` chip-${tone}` : ""}`}>{children}</span>;
}

function Criterion({ ac }: { ac: AcceptanceCriterion }) {
  return (
    <li className="gwt">
      <span className="gwt-id">{ac.id}</span>
      <dl className="gwt-body">
        <dt>Given</dt>
        <dd>{ac.given}</dd>
        <dt>When</dt>
        <dd>{ac.when}</dd>
        <dt>Then</dt>
        <dd>{ac.then}</dd>
      </dl>
    </li>
  );
}

function StoryCard({ story }: { story: Story }) {
  const isEnabler = story.type === "enabler";
  const isBaseline = story.origin === "baseline_recommendation";
  const criteria = story.acceptance_criteria || [];
  const checks = story.nfr_checks || [];
  const refs = story.requirement_refs || [];
  const deps = story.dependencies || [];

  return (
    <details className={`story${isEnabler ? " story-enabler" : ""}`}>
      <summary>
        <span className="story-meta">
          <span className="story-id">{story.id}</span>
          {isEnabler ? <Chip tone="enabler">enabler</Chip> : null}
          {isBaseline ? <Chip tone="baseline">baseline</Chip> : null}
          {story.priority ? <Chip tone="priority">{story.priority}</Chip> : null}
        </span>
        <span className="story-title">{story.title}</span>
      </summary>

      <div className="story-body">
        {story.need ? <p className="story-need">{story.need}</p> : null}

        <div className="story-kicker">Acceptance criteria</div>
        {criteria.length === 0 ? (
          <p className="muted">None recorded.</p>
        ) : (
          <ul className="gwt-list">
            {criteria.map((ac) => (
              <Criterion key={ac.id} ac={ac} />
            ))}
          </ul>
        )}

        {checks.length > 0 ? (
          <>
            <div className="story-kicker">Non-functional checks</div>
            <ul className="tradeoff-list">
              {checks.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </>
        ) : null}

        {refs.length > 0 || deps.length > 0 ? (
          <div className="story-foot">
            {refs.length > 0 ? (
              <span className="story-foot-group">
                <span className="story-foot-label">Traces to</span>
                {refs.map((r) => (
                  <Chip key={r} tone="trace">
                    {r}
                  </Chip>
                ))}
              </span>
            ) : null}
            {deps.length > 0 ? (
              <span className="story-foot-group">
                <span className="story-foot-label">Depends on</span>
                {deps.map((d) => (
                  <Chip key={d}>{d}</Chip>
                ))}
              </span>
            ) : null}
          </div>
        ) : null}

        {(story.requirement_texts || []).length > 0 ? (
          <blockquote className="story-source">
            {(story.requirement_texts || []).join(" ")}
          </blockquote>
        ) : null}
      </div>
    </details>
  );
}

export function DeliveryBacklog({ epics }: { epics: Epic[] }) {
  if (!epics || epics.length === 0) return null;

  const stories = epics.flatMap((e) => e.stories || []);
  const businessCount = stories.filter((s) => s.type !== "enabler").length;
  const enablerCount = stories.length - businessCount;

  return (
    <section className="backlog">
      <div className="backlog-head">
        <h2 className="artifact-h">
          <span className="artifact-n">13</span>
          <span className="artifact-t">Delivery backlog</span>
        </h2>
        <p className="muted">
          {epics.length} {epics.length === 1 ? "epic" : "epics"} ·{" "}
          {businessCount} user {businessCount === 1 ? "story" : "stories"} ·{" "}
          {enablerCount} {enablerCount === 1 ? "enabler" : "enablers"}. Evidenced
          stories cite their requirements; technical enablers are baseline
          recommendations, not traced evidence.
        </p>
      </div>

      {epics.map((epic) => (
        <article key={epic.id} className="epic panel blueprint">
          <i className="corner tl" />
          <i className="corner tr" />
          <i className="corner bl" />
          <i className="corner br" />

          <header className="epic-head">
            <div className="epic-ident">
              <span className="epic-id">{epic.id}</span>
              {epic.priority ? <Chip tone="priority">{epic.priority}</Chip> : null}
              {epic.origin === "baseline_recommendation" ? (
                <Chip tone="baseline">baseline</Chip>
              ) : null}
              <span className="muted epic-count">
                {(epic.stories || []).length}{" "}
                {(epic.stories || []).length === 1 ? "story" : "stories"}
              </span>
            </div>
            <h3 className="epic-title">{epic.title}</h3>
            {epic.need ? <p className="epic-need">{epic.need}</p> : null}
            {epic.business_outcome ? (
              <p className="epic-outcome">
                <span className="story-kicker">Outcome</span>
                {epic.business_outcome}
              </p>
            ) : null}
            {(epic.requirement_refs || []).length > 0 ? (
              <div className="epic-refs">
                {(epic.requirement_refs || []).map((r) => (
                  <Chip key={r} tone="trace">
                    {r}
                  </Chip>
                ))}
              </div>
            ) : null}
          </header>

          <div className="story-list">
            {(epic.stories || []).map((story) => (
              <StoryCard key={story.id} story={story} />
            ))}
          </div>
        </article>
      ))}
    </section>
  );
}
