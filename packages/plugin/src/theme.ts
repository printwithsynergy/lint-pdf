/**
 * LintPDF theme definition for the dashboard.
 *
 * Provides full branding, color palette, fonts, and CSS variable overrides
 * for the Pixie Dust theme system. Per-tenant branding for white-label
 * customization remains in the tenant model.
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
    emailFrom: "noreply@lintpdf.com",
    supportEmail: "support@lintpdf.com",
  },
  fonts: {
    sans: "Inter",
    display: "Inter",
    mono: "JetBrains Mono",
  },
  brandColors: {
    "50": "#eff6ff",
    "100": "#dbeafe",
    "200": "#bfdbfe",
    "300": "#93c5fd",
    "400": "#60a5fa",
    "500": "#3b82f6",
    "600": "#2563eb",
    "700": "#1d4ed8",
    "800": "#1e40af",
    "900": "#1e3a8a",
    "950": "#172554",
  },
  cssVariables: {
    "--primary": "224 69% 40%",
    "--primary-foreground": "0 0% 100%",
    "--accent": "217 91% 60%",
    "--accent-foreground": "0 0% 100%",
    "--login-ring": "224 69% 40%",
  },
});
