import { createConfig } from "@thinkneverland/pixie-dust-config";

export const config = createConfig({
  appName: "Never Grounded",
  cookieName: "grounded-session",
  emailFrom: "noreply@nevergrounded.io",
  allowSignUp: true,
  // waitlistEnabled is supported at runtime but not yet in the package types.
  waitlistEnabled: true,
} as Parameters<typeof createConfig>[0]);
