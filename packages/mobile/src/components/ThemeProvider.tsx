import { useEffect, type ReactNode } from "react";
import type { TenantBranding } from "../lib/types";

interface ThemeProviderProps {
  branding: TenantBranding | null;
  children: ReactNode;
}

/**
 * Applies the captured tenant's branding to the document root as
 * CSS custom properties so Tailwind's `brand-*` utilities pick them
 * up (see `globals.css`). When `branding` is null or missing
 * `primaryColor`, the original LintPDF blue palette wins via the
 * Tailwind fallback values.
 *
 * Mirrors the same pattern as `packages/desktop/src/components/ThemeProvider.tsx` —
 * keep them in sync so the two shells feel identical to a tenant.
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
