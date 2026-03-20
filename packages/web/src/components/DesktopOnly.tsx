"use client";

import { useEffect, useState, type ReactNode } from "react";

/**
 * Renders children only on md+ screens (≥ 768px).
 * Completely removes elements from the DOM on mobile to avoid
 * iOS WebKit GPU compositing artifacts from blur/filter effects.
 */
export function DesktopOnly({ children }: { children: ReactNode }) {
  const [isDesktop, setIsDesktop] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    setIsDesktop(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  if (!isDesktop) return null;
  return children;
}
