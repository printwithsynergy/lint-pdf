import { defineConfig } from "@playwright/test";

const API_BASE = process.env.API_BASE_URL ?? "https://api.lintpdf.com";
const WEB_BASE = process.env.WEB_BASE_URL ?? "https://lintpdf.com";

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
    baseURL: WEB_BASE,
    extraHTTPHeaders: { Accept: "application/json" },
    ignoreHTTPSErrors: true,
    trace: "on-first-retry",
    ...proxyConfig,
  },
  projects: [
    {
      name: "api-tests",
      testDir: "./e2e/api",
      use: { baseURL: API_BASE },
    },
    {
      name: "ui-tests",
      testDir: "./e2e/ui",
      use: {
        baseURL: WEB_BASE,
        browserName: "chromium",
      },
    },
    {
      name: "role-tests",
      testDir: "./e2e/roles",
      use: { baseURL: API_BASE },
    },
  ],
});
