"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

export function ProjectDeleteButton({
  projectId,
  projectName,
}: {
  projectId: string;
  projectName: string;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function onDelete() {
    const ok = window.confirm(
      `Delete “${projectName}”?\n\nThis permanently removes the project, interview answers, options, package, and exports. This cannot be undone.`,
    );
    if (!ok) return;

    startTransition(async () => {
      try {
        setError(null);
        const res = await fetch(`/api/backend/projects/${projectId}`, {
          method: "DELETE",
        });
        if (!res.ok && res.status !== 204) {
          const text = await res.text();
          throw new Error(text || `Delete failed (${res.status})`);
        }
        router.refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Delete failed");
      }
    });
  }

  return (
    <span style={{ display: "inline-flex", flexDirection: "column", gap: 4 }}>
      <button
        type="button"
        className="btn"
        style={{ padding: "6px 14px" }}
        disabled={pending}
        onClick={onDelete}
        aria-label={`Delete project ${projectName}`}
      >
        {pending ? "Deleting…" : "Delete"}
      </button>
      {error ? (
        <span className="muted" style={{ fontSize: 12, color: "#8a3a32", maxWidth: 180 }}>
          {error}
        </span>
      ) : null}
    </span>
  );
}
