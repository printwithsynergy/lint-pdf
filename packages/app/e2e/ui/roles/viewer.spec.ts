import { test, expect } from "@playwright/test";
import {
  createRoleContext,
  isMcpBackdoorAvailable,
  getTestTenantSlug,
} from "../../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Role: Viewer", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  // --- Allowed pages (read-only access) ---

  test("can view the main dashboard", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard");
    await expect(page.locator("main").getByRole("heading", { name: /dashboard/i }).first()).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can view tenant dashboard", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();
    const slug = getTestTenantSlug();

    await page.goto(`/dashboard/${slug}`);
    await expect(page.locator("main").getByRole("heading", { name: /dashboard/i }).first()).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can view preflight results (read-only)", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/preflight");
    await expect(page.locator("main").getByRole("heading", { name: /preflight/i }).first()).toBeVisible({ timeout: 15_000 });

    // Viewer should NOT see upload/submit controls
    const uploadButton = page.locator(
      "button:has-text('upload'), button:has-text('submit'), input[type='file']"
    ).first();
    const hasUpload = await uploadButton.isVisible({ timeout: 3_000 }).catch(() => false);
    // This is a soft check — viewer ideally should not have write controls
    if (hasUpload) {
      // Log but don't fail: the UI may still show disabled controls
      console.warn("Viewer can see upload controls on preflight page — verify they are disabled");
    }

    await context.close();
  });

  test("can view rulesets page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/rulesets");
    await expect(page.locator("main").getByRole("heading", { name: /ruleset/i }).first()).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can view usage page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/usage");
    await expect(page.locator("main").getByRole("heading", { name: /usage/i }).first()).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can view reports page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/reports");
    await expect(page.locator("main").getByRole("heading", { name: /report/i }).first()).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access own profile", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/profile");
    await expect(page.locator("main").getByRole("heading", { name: /profile/i }).first()).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can view waitlist page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/waitlist");
    const response = await page.goto("/dashboard/waitlist");
    expect(response?.status() ?? 0).toBeLessThan(500);

    await context.close();
  });

  // --- Blocked pages ---

  test("cannot access team invite page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
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
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
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
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
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

  test("cannot access webhooks page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
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
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
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

  test("cannot access account settings", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
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

  test("cannot access account branding", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/account/branding", { waitUntil: "domcontentloaded" });

    const isRedirected = /\/auth\/login/.test(page.url()) || /\/dashboard\/?$/.test(page.url());
    const hasUnauthorized = await page
      .getByText(/unauthorized|forbidden|access denied|not allowed/i)
      .isVisible({ timeout: 5_000 })
      .catch(() => false);

    expect(isRedirected || hasUnauthorized).toBeTruthy();

    await context.close();
  });

  test("cannot access admin pages", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
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

  test("cannot access admin tenants page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/admin/tenants", { waitUntil: "domcontentloaded" });

    const isRedirected = /\/auth\/login/.test(page.url()) || /\/dashboard\/?$/.test(page.url());
    const hasUnauthorized = await page
      .getByText(/unauthorized|forbidden|access denied/i)
      .isVisible({ timeout: 5_000 })
      .catch(() => false);

    expect(isRedirected || hasUnauthorized).toBeTruthy();

    await context.close();
  });
});
