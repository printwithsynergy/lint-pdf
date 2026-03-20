/**
 * LintPDF theme definition using Pixie Dust Theme Kit.
 *
 * Defines the LintPDF brand identity for the Pixie Dust dashboard.
 * Per-tenant branding for white-label customization remains in the
 * tenant model (brand_name, brand_logo_url, brand_primary_color, etc.).
 */

import { defineTheme } from "@thinkneverland/pixie-dust-theme-kit";

export const lintpdfTheme = defineTheme({
  name: "lintpdf",
  displayName: "LintPDF",
  metadata: {
    title: "LintPDF — Preflights you won't hate.",
    description:
      "LintPDF — the Pixie Dust-powered SaaS platform by Think Neverland.",
    themeColor: "#0ea5e9",
  },
  brand: {
    companyName: "Think Neverland",
    siteUrl: "https://lintpdf.com",
  },
  cssVariables: {
    "--primary": "199 89% 48%",
    "--primary-foreground": "0 0% 100%",
    "--accent": "199 95% 74%",
    "--accent-foreground": "201 90% 27%",
  },
});
