import { ArtifactPanel } from "@/components/ArtifactPanel";

export type BacklogItem = {
  id: string;
  title: string;
  priority?: string;
  area?: string;
  notes?: string;
  acceptance_criteria?: string[];
  dependencies?: string[];
  item_type?: string;
};

/**
 * Artifact 12 — cross-cutting architecture work (auth, observability, drills).
 * Distinct from artifact 13, which is the delivery backlog of epics and user
 * stories traced to stated requirements.
 */
export function ArchitectureBacklog({ items }: { items: BacklogItem[] }) {
  return (
    <ArtifactPanel n="12" title="Architecture backlog">
      {items.length === 0 ? (
        <p className="muted">No backlog items.</p>
      ) : (
        <>
          <p className="muted artifact-lede">
            {items.length} {items.length === 1 ? "item" : "items"} of
            cross-cutting technical work every feature depends on. Delivery work
            traced to requirements lives in artifact 13 (Delivery backlog).
          </p>
          <ul className="ab-list">
            {items.map((item) => {
              const criteria = item.acceptance_criteria || [];
              const deps = item.dependencies || [];
              return (
                <li key={item.id} className="ab-item">
                  <div className="ab-meta">
                    <span className="ab-id">{item.id}</span>
                    {item.priority ? (
                      <span className="chip chip-priority">{item.priority}</span>
                    ) : null}
                    {item.area ? <span className="chip">{item.area}</span> : null}
                    {item.item_type ? (
                      <span className="chip chip-enabler">{item.item_type}</span>
                    ) : null}
                  </div>
                  <h3 className="ab-title">{item.title}</h3>
                  {item.notes ? <p className="ab-note">{item.notes}</p> : null}
                  {criteria.length > 0 ? (
                    <>
                      <div className="story-kicker">Acceptance criteria</div>
                      <ul className="tradeoff-list">
                        {criteria.map((c) => (
                          <li key={c}>{c}</li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                  {deps.length > 0 ? (
                    <div className="story-foot">
                      <span className="story-foot-group">
                        <span className="story-foot-label">Depends on</span>
                        {deps.map((d) => (
                          <span key={d} className="chip">
                            {d}
                          </span>
                        ))}
                      </span>
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </>
      )}
    </ArtifactPanel>
  );
}
