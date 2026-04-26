import { useEffect, type ReactNode } from "react";
import type { TenantBranding } from "../lib/types";

interface ThemeProviderProps {
  branding: TenantBranding | null;
  children: ReactNode;
}

/**
 * Applies the captured tenant's branding to the document root as
 * CSS custom properties so Tailwind's `brand-*` utilities pick them
 * up (see tailwind.config.ts). When `branding` is null or missing
 * `primaryColor`, the original hardcoded blue palette wins via the
 * Tailwind fallback values.
 *
 * Only `primaryColor` is applied as a derived scale today — multi-
 * shade harmonization (light/dark variants of the primary) is left
 * to a future iteration. The 600/700/500 shades are the ones the
 * existing UI uses most, so a single primary swap is enough to make
 * the app feel branded.
 */
export function ThemeProvider({ branding, children }: ThemeProviderProps) {
  useEffect(() => {
    const root = document.documentElement;
    const primary = branding?.primaryColor;
    if (!primary || typeof primary !== "string") {
      root.style.removeProperty("--brand-500");
      root.style.removeProperty("--brand-600");
      root.style.removeProperty("--brand-700");
      return;
    }

    const rgb = hexToRgb(primary);
    if (!rgb) return;

    const triple = `${rgb.r} ${rgb.g} ${rgb.b}`;
    root.style.setProperty("--brand-500", triple);
    root.style.setProperty("--brand-600", triple);
    // Slight darken for hover/active so the existing 700 utility stays
    // perceptually distinct from 600. Cheap luma shift — no full
    // color-space conversion needed for a single-step darken.
    const darker = darkenRgb(rgb, 0.85);
    root.style.setProperty(
      "--brand-700",
      `${darker.r} ${darker.g} ${darker.b}`,
    );
  }, [branding]);

  return <>{children}</>;
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const cleaned = hex.trim().replace(/^#/, "");
  if (cleaned.length !== 3 && cleaned.length !== 6) return null;
  const full =
    cleaned.length === 3
      ? cleaned
          .split("")
          .map((c) => c + c)
          .join("")
      : cleaned;
  const num = parseInt(full, 16);
  if (Number.isNaN(num)) return null;
  return {
    r: (num >> 16) & 0xff,
    g: (num >> 8) & 0xff,
    b: num & 0xff,
  };
}

function darkenRgb(
  rgb: { r: number; g: number; b: number },
  factor: number,
): { r: number; g: number; b: number } {
  return {
    r: Math.round(rgb.r * factor),
    g: Math.round(rgb.g * factor),
    b: Math.round(rgb.b * factor),
  };
}
