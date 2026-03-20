/**
 * Grounded theme definition using Pixie Dust Theme Kit.
 *
 * Defines the Never Grounded brand identity for the Pixie Dust dashboard.
 * Per-tenant branding for white-label customization remains in the
 * tenant model (brand_name, brand_logo_url, brand_primary_color, etc.).
 */

import { defineTheme } from "@thinkneverland/pixie-dust-theme-kit";

export const groundedTheme = defineTheme({
  name: "grounded",
  displayName: "Never Grounded",
  metadata: {
    title: "Never Grounded — Built to sail. Cleared for press.",
    description:
      "Never Grounded — the Pixie Dust-powered SaaS platform by Think Neverland.",
    themeColor: "#162d60",
  },
  brand: {
    companyName: "Think Neverland",
    siteUrl: "https://nevergrounded.io",
  },
  cssVariables: {
    "--primary": "220 63% 23%",
    "--primary-foreground": "0 0% 98%",
    "--accent": "207 55% 57%",
    "--accent-foreground": "0 0% 98%",
  },
});
