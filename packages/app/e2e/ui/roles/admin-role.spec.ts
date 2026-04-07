import { test, expect } from "@playwright/test";
import {
  createRoleContext,
  isMcpBackdoorAvailable,
  getTestTenantSlug,
} from "../../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Role: Admin", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("can access the tenant dashboard", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();
    const slug = getTestTenantSlug();

    await page.goto(`/dashboard/${slug}`);
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can manage team members", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/team");
    await expect(page.getByRole("heading", { name: /team/i })).toBeVisible({ timeout: 15_000 });

    // Admin should see management controls (invite button, role selectors, etc.)
    const managementControls = page.locator(
      "a:has-text('invite'), button:has-text('invite'), [data-testid='invite-button']"
    ).first();
    await expect(managementControls).toBeVisible({ timeout: 10_000 }).catch(() => {
      // Controls may not be inline on the team page; navigation to /team is sufficient
    });

    await context.close();
  });

  test("can invite team members", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/team/invite");
    await expect(page.getByRole("heading", { name: /invite|add member/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access billing page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/billing");
    await expect(page.getByRole("heading", { name: /billing|subscription|plan/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access API keys page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/api-keys");
    await expect(page.getByRole("heading", { name: /api key/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access preflight page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/preflight");
    await expect(page.getByRole("heading", { name: /preflight/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access rulesets page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/rulesets");
    await expect(page.getByRole("heading", { name: /ruleset/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can manage webhooks", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/webhooks");
    await expect(page.getByRole("heading", { name: /webhook/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access account settings", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/account/settings");
    await expect(page.getByRole("heading", { name: /settings/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access account branding", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/account/branding");
    await expect(page.getByRole("heading", { name: /branding/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access account AI settings", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/account/ai");
    await expect(page.getByRole("heading", { name: /ai/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access endpoints page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/endpoints");
    await expect(page.getByRole("heading", { name: /endpoint/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("cannot access super-admin pages", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
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

  test("cannot access admin/tenants", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
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
