/**
 * LintPDF theme definition for the dashboard.
 *
 * Per-tenant branding for white-label customization remains in the
 * tenant model (brand_name, brand_logo_url, brand_primary_color, etc.).
 */

import { defineTheme } from "@thinkneverland/pixie-dust-theme-kit";

export const lintpdfTheme = defineTheme({
  name: "lintpdf",
  displayName: "LintPDF",
  metadata: {
    title: "LintPDF — Preflights you won't hate.",
    description: "LintPDF — PDF preflight SaaS by Think Neverland.",
    themeColor: "#1e40af",
  },
  brand: {
    companyName: "Think Neverland",
    siteUrl: "https://lintpdf.com",
  },
  cssVariables: {
    "--primary": "224 69% 40%",
    "--primary-foreground": "0 0% 100%",
    "--accent": "217 91% 60%",
    "--accent-foreground": "224 76% 33%",
  },
});
