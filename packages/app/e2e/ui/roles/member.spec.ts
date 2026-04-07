import { test, expect } from "@playwright/test";
import {
  createRoleContext,
  isMcpBackdoorAvailable,
  getTestTenantSlug,
} from "../../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Role: Member", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("can access the main dashboard", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access tenant dashboard", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();
    const slug = getTestTenantSlug();

    await page.goto(`/dashboard/${slug}`);
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can view preflight jobs and results", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/preflight");
    await expect(page.getByRole("heading", { name: /preflight/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can view rulesets page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/rulesets");
    await expect(page.getByRole("heading", { name: /ruleset/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can view usage page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/usage");
    await expect(page.getByRole("heading", { name: /usage/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can view reports page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/reports");
    await expect(page.getByRole("heading", { name: /report/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access own profile", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/profile");
    await expect(page.getByRole("heading", { name: /profile/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can view team page with limited access", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/team");

    // Page should load (members can view team list) but may have limited controls
    const status = (await page.goto("/dashboard/team"))?.status() ?? 0;
    expect(status).toBeLessThan(500);

    await context.close();
  });

  test("cannot access team invite page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/team/invite", { waitUntil: "domcontentloaded" });

    const isRedirected = /\/auth\/login/.test(page.url()) || /\/dashboard\/?$/.test(page.url());
    const hasUnauthorized = await page
      .getByText(/unauthorized|forbidden|access denied|not allowed/i)
      .isVisible({ timeout: 5_000 })
      .catch(() => false);

    expect(isRedirected || hasUnauthorized).toBeTruthy();

    await context.close();
  });

  test("cannot access billing page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/billing", { waitUntil: "domcontentloaded" });

    const isRedirected = /\/auth\/login/.test(page.url()) || /\/dashboard\/?$/.test(page.url());
    const hasUnauthorized = await page
      .getByText(/unauthorized|forbidden|access denied|not allowed/i)
      .isVisible({ timeout: 5_000 })
      .catch(() => false);

    expect(isRedirected || hasUnauthorized).toBeTruthy();

    await context.close();
  });

  test("cannot access API keys page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/api-keys", { waitUntil: "domcontentloaded" });

    const isRedirected = /\/auth\/login/.test(page.url()) || /\/dashboard\/?$/.test(page.url());
    const hasUnauthorized = await page
      .getByText(/unauthorized|forbidden|access denied|not allowed/i)
      .isVisible({ timeout: 5_000 })
      .catch(() => false);

    expect(isRedirected || hasUnauthorized).toBeTruthy();

    await context.close();
  });

  test("cannot access account settings", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/account/settings", { waitUntil: "domcontentloaded" });

    const isRedirected = /\/auth\/login/.test(page.url()) || /\/dashboard\/?$/.test(page.url());
    const hasUnauthorized = await page
      .getByText(/unauthorized|forbidden|access denied|not allowed/i)
      .isVisible({ timeout: 5_000 })
      .catch(() => false);

    expect(isRedirected || hasUnauthorized).toBeTruthy();

    await context.close();
  });

  test("cannot access webhooks page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/webhooks", { waitUntil: "domcontentloaded" });

    const isRedirected = /\/auth\/login/.test(page.url()) || /\/dashboard\/?$/.test(page.url());
    const hasUnauthorized = await page
      .getByText(/unauthorized|forbidden|access denied|not allowed/i)
      .isVisible({ timeout: 5_000 })
      .catch(() => false);

    expect(isRedirected || hasUnauthorized).toBeTruthy();

    await context.close();
  });

  test("cannot access endpoints page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/endpoints", { waitUntil: "domcontentloaded" });

    const isRedirected = /\/auth\/login/.test(page.url()) || /\/dashboard\/?$/.test(page.url());
    const hasUnauthorized = await page
      .getByText(/unauthorized|forbidden|access denied|not allowed/i)
      .isVisible({ timeout: 5_000 })
      .catch(() => false);

    expect(isRedirected || hasUnauthorized).toBeTruthy();

    await context.close();
  });

  test("cannot access admin pages", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/admin", { waitUntil: "domcontentloaded" });

    const isRedirected = /\/auth\/login/.test(page.url()) || /\/dashboard\/?$/.test(page.url());
    const hasUnauthorized = await page
      .getByText(/unauthorized|forbidden|access denied/i)
      .isVisible({ timeout: 5_000 })
      .catch(() => false);

    expect(isRedirected || hasUnauthorized).toBeTruthy();

    await context.close();
  });
});
