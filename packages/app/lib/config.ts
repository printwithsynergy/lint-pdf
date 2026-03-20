import { createConfig } from "@thinkneverland/pixie-dust-config";

export const config = createConfig({
  appName: "LintPDF",
  cookieName: "lintpdf-session",
  emailFrom: "noreply@lintpdf.com",
  allowSignUp: true,
  // waitlistEnabled is supported at runtime but not yet in the package types.
  waitlistEnabled: true,
} as Parameters<typeof createConfig>[0]);
