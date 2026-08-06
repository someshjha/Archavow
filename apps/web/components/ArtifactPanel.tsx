import type { ReactNode } from "react";
import { MarkdownBody } from "@/components/MarkdownBody";
import { artifactDoc } from "@/lib/artifacts";

export function ArtifactHeading({
  n,
  title,
  conditional,
}: {
  n: string;
  title: string;
  conditional?: boolean;
}) {
  return (
    <h2 className="artifact-h">
      {n ? <span className="artifact-n">{n}</span> : null}
      <span className="artifact-t">{title}</span>
      {conditional ? <span className="tag">draft</span> : null}
    </h2>
  );
}

/** Blueprint panel with a catalog-numbered heading. */
export function ArtifactPanel({
  n,
  title,
  conditional,
  children,
}: {
  n: string;
  title: string;
  conditional?: boolean;
  children: ReactNode;
}) {
  return (
    <section className="panel blueprint artifact">
      <i className="corner tl" />
      <i className="corner tr" />
      <i className="corner bl" />
      <i className="corner br" />
      <ArtifactHeading n={n} title={title} conditional={conditional} />
      {children}
    </section>
  );
}

/**
 * One markdown artifact from `package.documents`. Renders nothing when the
 * document is absent, so a package built before an artifact existed simply
 * skips it instead of showing an empty numbered panel.
 */
export function ArtifactDocPanel({
  docKey,
  docs,
}: {
  docKey: string;
  docs: Record<string, string>;
}) {
  const body = (docs[docKey] || "").trim();
  if (!body) return null;
  const { n, title, conditional } = artifactDoc(docKey);
  return (
    <ArtifactPanel n={n} title={title} conditional={conditional}>
      <MarkdownBody>{body}</MarkdownBody>
    </ArtifactPanel>
  );
}
