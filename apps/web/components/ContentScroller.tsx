"use client";

import { ReactLenis } from "lenis/react";
import { useEffect, useState } from "react";

export function ContentScroller({ children }: { children: React.ReactNode }) {
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setEnabled(!media.matches);
    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);

  if (!enabled) {
    return <div className="af-content">{children}</div>;
  }

  return (
    <ReactLenis
      className="af-content"
      root
      options={{ autoRaf: true, lerp: 0.09, smoothWheel: true }}
    >
      {children}
    </ReactLenis>
  );
}
