import { defineTheme } from "@thinkneverland/pixie-dust-theme-kit";

export default defineTheme({
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
    "--primary": "224 69% 40%",
    "--primary-foreground": "0 0% 100%",
    "--accent": "217 91% 60%",
    "--accent-foreground": "224 76% 33%",
  },
});
