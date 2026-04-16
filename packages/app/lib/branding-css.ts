/**
 * Translate AppSettings hex colors into CSS custom-property overrides that
 * the Pixie Dust theme (and Tailwind utilities like `bg-primary`) consume as
 * HSL triplets, e.g. `hsl(var(--primary))`.
 *
 * Injected via `DashboardShell`'s `customCss` prop so Tenant branding from
 * the DB actually repaints the dashboard.
 */

function hexToHslTriplet(hex: string): string | null {
  const clean = hex.trim().replace(/^#/, "");
  const m =
    clean.length === 3
      ? clean
          .split("")
          .map((c) => c + c)
          .join("")
      : clean.length === 6
        ? clean
        : null;
  if (!m || !/^[0-9a-fA-F]{6}$/.test(m)) return null;

  const r = parseInt(m.slice(0, 2), 16) / 255;
  const g = parseInt(m.slice(2, 4), 16) / 255;
  const b = parseInt(m.slice(4, 6), 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r:
        h = (g - b) / d + (g < b ? 6 : 0);
        break;
      case g:
        h = (b - r) / d + 2;
        break;
      case b:
        h = (r - g) / d + 4;
        break;
    }
    h *= 60;
  }

  return `${Math.round(h)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%`;
}

export interface BrandingColors {
  primaryColor?: string | null;
  accentColor?: string | null;
  sidebarBgColor?: string | null;
  sidebarTextColor?: string | null;
  sidebarAccentColor?: string | null;
  loginBgColor?: string | null;
  loginCardColor?: string | null;
  loginTextColor?: string | null;
  loginInputColor?: string | null;
  loginRingColor?: string | null;
  themeTokenOverrides?: string | null;
}

const MAPPING: Array<[keyof BrandingColors, string]> = [
  ["primaryColor", "--primary"],
  ["accentColor", "--accent"],
  ["sidebarBgColor", "--sidebar"],
  ["sidebarTextColor", "--sidebar-foreground"],
  ["sidebarAccentColor", "--sidebar-accent"],
  ["loginBgColor", "--login-bg"],
  ["loginCardColor", "--login-card"],
  ["loginTextColor", "--login-text"],
  ["loginInputColor", "--login-input"],
  ["loginRingColor", "--login-ring"],
];

export function buildBrandingCss(branding: BrandingColors): string {
  const lines: string[] = [];
  for (const [field, cssVar] of MAPPING) {
    const value = branding[field];
    if (!value || typeof value !== "string") continue;
    const hsl = hexToHslTriplet(value);
    if (!hsl) continue;
    lines.push(`  ${cssVar}: ${hsl};`);
  }

  // `themeTokenOverrides` is a JSON blob of { [cssVarName]: rawValue } that the
  // Pixie Dust ThemeTokenEditor writes. Apply each entry verbatim — rawValue
  // is expected to already be a valid CSS value (hsl(...), #hex, or triplet).
  if (branding.themeTokenOverrides) {
    try {
      const parsed = JSON.parse(branding.themeTokenOverrides) as Record<
        string,
        unknown
      >;
      for (const [key, raw] of Object.entries(parsed)) {
        if (typeof raw !== "string" || !raw.trim()) continue;
        const varName = key.startsWith("--") ? key : `--${key}`;
        if (!/^--[a-zA-Z0-9-]+$/.test(varName)) continue;
        lines.push(`  ${varName}: ${raw.replace(/[;{}]/g, "").trim()};`);
      }
    } catch {
      // Malformed JSON — skip silently so one bad row doesn't wipe out branding.
    }
  }

  if (lines.length === 0) return "";
  return `:root {\n${lines.join("\n")}\n}`;
}
