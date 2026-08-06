"use client";

import Link from "next/link";
import { motion } from "motion/react";

export type LifecycleStage =
  | "intake"
  | "interview"
  | "options"
  | "package"
  | "export";

const STEPS: { id: LifecycleStage; label: string; path: string }[] = [
  { id: "intake", label: "Onboarding", path: "new" },
  { id: "interview", label: "Interview", path: "interview" },
  { id: "options", label: "Options", path: "options" },
  { id: "package", label: "Package", path: "package" },
  { id: "export", label: "Export", path: "export" },
];

export function Stepper({
  current,
  projectId,
  reachedStage,
}: {
  current: LifecycleStage;
  projectId?: string;
  /** Furthest stage reached — links enable through this index. */
  reachedStage?: LifecycleStage;
}) {
  const order = STEPS.map((s) => s.id);
  const idx = order.indexOf(current);
  const reachedIdx = order.indexOf(reachedStage ?? current);

  return (
    <div className="stepper">
      {STEPS.map((step, i) => {
        const state =
          i < idx ? "done" : i === idx ? "on" : "future";
        const linkable =
          Boolean(projectId) &&
          step.id !== "intake" &&
          i <= Math.max(idx, reachedIdx);
        const href =
          projectId && step.id !== "intake"
            ? `/projects/${projectId}/${step.path}`
            : null;

        const inner = (
          <motion.span
            className={`step ${state}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: i * 0.08 }}
          >
            <span className="n">{state === "done" ? "✓" : i + 1}</span>
            {step.label}
          </motion.span>
        );

        return (
          <span
            key={step.id}
            style={{ display: "inline-flex", alignItems: "center" }}
          >
            {i > 0 ? <span className="connector" /> : null}
            {linkable && href ? (
              <Link href={href} style={{ textDecoration: "none" }}>
                {inner}
              </Link>
            ) : (
              inner
            )}
          </span>
        );
      })}
    </div>
  );
}

export function CancelLink() {
  return (
    <Link href="/" className="btn">
      Cancel
    </Link>
  );
}
