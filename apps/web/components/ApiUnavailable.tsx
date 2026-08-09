import Link from "next/link";

/**
 * Shown when a server component can't reach the API at all (connection
 * refused, DNS failure, timeout) — as opposed to a valid API response that
 * says "not ready yet." Keeps the raw error out of the headline (it's a
 * Node fetch message like "fetch failed", not something a user should have
 * to parse) but still surfaces it, tucked away, for anyone debugging.
 */
export function ApiUnavailable({
  detail,
  action,
}: {
  detail?: string;
  action?: { href: string; label: string };
}) {
  return (
    <div className="api-offline" role="alert">
      <div className="api-offline-kicker">Connection</div>
      <h2>Can&apos;t reach the API</h2>
      <p className="muted" style={{ marginBottom: 0 }}>
        The web app can&apos;t reach the Archavow API right now. Is it running?
        Try <code>make up</code> from the project root, then refresh.
      </p>
      {action ? (
        <div className="form-actions" style={{ marginTop: 16 }}>
          <Link href={action.href} className="btn">
            {action.label}
          </Link>
        </div>
      ) : null}
      {detail ? (
        <details className="api-offline-detail">
          <summary>Technical detail</summary>
          <code>{detail}</code>
        </details>
      ) : null}
    </div>
  );
}
