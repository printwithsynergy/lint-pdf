import { defineConfig } from "@playwright/test";

const hasAppUrl = !!process.env.APP_BASE_URL;
const hasDb = !!process.env.DATABASE_URL;
const isLocal = !hasAppUrl && hasDb;
const APP_BASE = process.env.APP_BASE_URL || (isLocal ? "http://localhost:3001" : "https://app.lintpdf.com");

// Support HTTP proxy for sandboxed environments
const proxyServer = process.env.HTTPS_PROXY || process.env.HTTP_PROXY;
const proxyConfig = proxyServer ? { proxy: { server: proxyServer } } : {};

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  retries: 1,
  reporter: [["html", { open: "never" }], ["list"]],
  globalSetup: "./e2e/fixtures/test-setup.ts",
  use: {
    baseURL: APP_BASE,
    ignoreHTTPSErrors: true,
    trace: "on-first-retry",
    ...proxyConfig,
  },
  // Spin up local dev server when DATABASE_URL is set but no external URL
  ...(isLocal
    ? {
        webServer: {
          command: "pnpm dev",
          port: 3001,
          reuseExistingServer: true,
          timeout: 60_000,
        },
      }
    : {}),
  projects: [
    {
      name: "api-tests",
      testDir: "./e2e/api",
      use: { baseURL: APP_BASE, extraHTTPHeaders: { Accept: "application/json" } },
    },
    {
      name: "ui-tests",
      testDir: "./e2e/ui",
      use: {
        baseURL: APP_BASE,
        browserName: "chromium",
      },
    },
    {
      name: "roles-tests",
      testDir: "./e2e/ui/roles",
      timeout: 180_000,
      use: {
        baseURL: APP_BASE,
        browserName: "chromium",
      },
    },
    {
      name: "preflight-tests",
      testDir: "./e2e/preflight",
      timeout: 300_000, // 5 min — PDF processing can be slow
      use: {
        baseURL: APP_BASE,
        extraHTTPHeaders: { Accept: "application/json" },
      },
    },
  ],
});
