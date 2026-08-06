import type { Metadata } from "next";
import "lenis/dist/lenis.css";
import "./globals.css";
import { WorkspaceAuthGate } from "./components/WorkspaceAuthGate";

export const metadata: Metadata = {
  title: "Archavow",
  description: "Build better systems before writing code.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <WorkspaceAuthGate>{children}</WorkspaceAuthGate>
      </body>
    </html>
  );
}
