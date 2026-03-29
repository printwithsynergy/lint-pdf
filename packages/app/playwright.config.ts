import { defineConfig } from "@playwright/test";

const isLocal = !process.env.APP_BASE_URL;
const APP_BASE = process.env.APP_BASE_URL ?? (isLocal ? "http://localhost:3001" : "https://app.lintpdf.com");

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
  use: {
    baseURL: APP_BASE,
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
      use: { baseURL: APP_BASE },
    },
    {
      name: "ui-tests",
      testDir: "./e2e/ui",
      use: {
        baseURL: APP_BASE,
        browserName: "chromium",
      },
    },
  ],
});
