import { defineTheme } from "@thinkneverland/pixie-dust-theme-kit";

export default defineTheme({
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
    // logoPath/faviconPath are supported at runtime but not yet in ThemeBrand type.
    ...({ logoPath: "/logo.svg", faviconPath: "/favicon.svg" } as Record<
      string,
      string
    >),
  },
  fonts: {
    sans: "Inter",
    mono: "JetBrains Mono",
  },
  cssVariables: {
    "--primary": "220 63% 23%",
    "--primary-foreground": "0 0% 98%",
    "--accent": "207 55% 57%",
    "--accent-foreground": "0 0% 98%",
  },
});
