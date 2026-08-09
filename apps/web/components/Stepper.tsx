import Link from "next/link";

export type LifecycleStage =
  | "intake"
  | "interview"
  | "options"
  | "package"
  | "export";

/** Stage order and paths — reused by AppShell's persistent stage rail. */
export const STEPS: { id: LifecycleStage; label: string; path: string }[] = [
  { id: "intake", label: "Onboarding", path: "new" },
  { id: "interview", label: "Interview", path: "interview" },
  { id: "options", label: "Options", path: "options" },
  { id: "package", label: "Package", path: "package" },
  { id: "export", label: "Export", path: "export" },
];

export function CancelLink() {
  return (
    <Link href="/" className="btn">
      Cancel
    </Link>
  );
}
