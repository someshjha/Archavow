"use client";

import { useRouter } from "next/navigation";

/**
 * Real history.back() rather than a fixed href — pages like Package track
 * which artifact is open via a URL query param (?a=...), so a static link
 * back to the bare route silently resets that instead of returning to
 * exactly where the user was.
 */
export function BackLink({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  return (
    <button type="button" onClick={() => router.back()} className="back-link">
      {children}
    </button>
  );
}
