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
    // Core
    "--primary": "224 69% 40%",
    "--primary-foreground": "0 0% 100%",
    "--accent": "217 91% 60%",
    "--accent-foreground": "0 0% 100%",
    // Sidebar
    "--sidebar": "220 20% 97%",
    "--sidebar-foreground": "220 30% 10%",
    "--sidebar-accent": "210 13% 93%",
    "--sidebar-border": "210 13% 91%",
    // Status
    "--success": "160 84% 39%",
    "--success-foreground": "0 0% 100%",
    "--warning": "45 93% 47%",
    "--warning-foreground": "0 0% 100%",
    "--info": "217 91% 60%",
    "--info-foreground": "0 0% 100%",
    // Admin / Impersonation
    "--admin": "217 91% 60%",
    "--admin-foreground": "0 0% 100%",
    "--impersonation": "38 92% 50%",
    "--impersonation-foreground": "40 96% 7%",
    // Login page
    "--login-bg": "240 20% 4%",
    "--login-card": "240 14% 12%",
    "--login-text": "240 10% 95%",
    "--login-text-muted": "240 8% 58%",
    "--login-text-subtle": "240 8% 37%",
    "--login-input": "240 18% 7%",
    "--login-ring": "224 69% 40%",
  },
});
