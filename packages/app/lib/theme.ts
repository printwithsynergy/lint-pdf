import { defineTheme } from "@thinkneverland/pixie-dust-theme-kit";

export default defineTheme({
  name: "lintpdf",
  displayName: "LintPDF",
  metadata: {
    title: "LintPDF — Every check. Every page. Every time.",
    description:
      "LintPDF — the Pixie Dust-powered SaaS platform by Think Neverland.",
    themeColor: "#0ea5e9",
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
    "--primary": "199 89% 48%",
    "--primary-foreground": "0 0% 100%",
    "--accent": "199 95% 74%",
    "--accent-foreground": "201 90% 27%",
  },
});
