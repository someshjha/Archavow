"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AmbientBackground } from "./AmbientBackground";
import { ContentScroller } from "./ContentScroller";

const NAV = [
  { href: "/", label: "Projects" },
  { href: "/projects/new", label: "New" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/settings", label: "Settings" },
];

export function AppShell({
  children,
  wide = false,
}: {
  children: React.ReactNode;
  wide?: boolean;
}) {
  const pathname = usePathname();

  return (
    <div className="af-shell">
      <AmbientBackground />
      <ContentScroller>
        <nav className="nav">
          <Link href="/" className="nav-brand">
            Archavow
          </Link>
          {NAV.map((item) => {
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <main className={wide ? "page page-wide" : "page"}>{children}</main>
      </ContentScroller>
    </div>
  );
}
