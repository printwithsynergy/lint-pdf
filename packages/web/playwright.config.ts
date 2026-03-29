import { defineConfig } from "@playwright/test";

const hasApiUrl = !!process.env.API_BASE_URL;
const hasWebUrl = !!process.env.WEB_BASE_URL;
const isLocal = !hasWebUrl && !hasApiUrl;
const WEB_BASE = process.env.WEB_BASE_URL ?? (isLocal ? "http://localhost:3000" : "https://lintpdf.com");
const API_BASE = process.env.API_BASE_URL ?? "https://api.lintpdf.com";

// Support HTTP proxy for sandboxed environments
const proxyServer = process.env.HTTPS_PROXY || process.env.HTTP_PROXY;
const proxyConfig = proxyServer ? { proxy: { server: proxyServer } } : {};

// API and role tests require the Python engine — only include when API_BASE_URL is set
const apiProjects = hasApiUrl
  ? [
      {
        name: "api-tests" as const,
        testDir: "./e2e/api",
        use: { baseURL: API_BASE },
      },
      {
        name: "role-tests" as const,
        testDir: "./e2e/roles",
        use: { baseURL: API_BASE },
      },
    ]
  : [];

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  retries: 1,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL: WEB_BASE,
    extraHTTPHeaders: { Accept: "application/json" },
    ignoreHTTPSErrors: true,
    trace: "on-first-retry",
    ...proxyConfig,
  },
  // Spin up local dev server when no external URL is provided
  ...(isLocal
    ? {
        webServer: {
          command: "pnpm dev",
          port: 3000,
          reuseExistingServer: true,
          timeout: 60_000,
        },
      }
    : {}),
  projects: [
    ...apiProjects,
    {
      name: "ui-tests",
      testDir: "./e2e/ui",
      use: {
        baseURL: WEB_BASE,
        browserName: "chromium",
      },
    },
  ],
});
