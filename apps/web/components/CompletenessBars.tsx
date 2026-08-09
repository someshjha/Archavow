import type { CompletenessCategory } from "@/lib/api";

export type BarTone = "ok" | "warn" | "bad";

export function Bar({
  label,
  value,
  tone = "ok",
  note,
  emphasis = false,
}: {
  label: string;
  value: number;
  tone?: BarTone;
  note?: string | null;
  emphasis?: boolean;
}) {
  return (
    <div className={`bar-block${emphasis ? " bar-block-lead" : ""}`}>
      <div className="bar-label">
        <span>{label}</span>
        <span className="bar-value">{value}</span>
      </div>
      <div className={`bar tone-${tone}`}>
        <span style={{ width: `${Math.max(value, value > 0 ? 2 : 1)}%` }} />
      </div>
      {note ? <p className="bar-note">{note}</p> : null}
    </div>
  );
}

export function toneFor(cat: CompletenessCategory): BarTone {
  if (cat.score >= cat.floor) return "ok";
  return cat.score * 2 < cat.floor ? "bad" : "warn";
}

export function noteFor(cat: CompletenessCategory): string | null {
  const open = cat.open_labels.join(", ");
  if (cat.score < cat.floor) {
    return open ? `needs ${cat.floor} · open: ${open}` : `needs ${cat.floor}`;
  }
  return open ? `open: ${open}` : null;
}
