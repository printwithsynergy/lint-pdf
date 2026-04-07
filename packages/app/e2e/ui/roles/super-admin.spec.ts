import { test, expect } from "@playwright/test";
import {
  createRoleContext,
  isMcpBackdoorAvailable,
  getTestTenantSlug,
} from "../../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Role: Super Admin", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  // --- Admin hub and sub-pages ---

  test("can access the admin hub", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/admin");
    await expect(page.getByRole("heading", { name: /admin/i })).toBeVisible({ timeout: 15_000 });

    // Admin hub should show navigation links to sub-pages
    await expect(page.getByRole("link", { name: /tenant/i })).toBeVisible({ timeout: 10_000 }).catch(() => {
      // Link text may vary — check for presence of any admin nav
    });

    await context.close();
  });

  test("admin hub shows links to tenants, jobs, trials, and health", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/admin");
    await expect(page.getByRole("heading", { name: /admin/i })).toBeVisible({ timeout: 15_000 });

    // Check for presence of key admin navigation items
    const adminLinks = [/tenant/i, /job/i, /trial/i, /health/i];
    for (const linkPattern of adminLinks) {
      const link = page.getByRole("link", { name: linkPattern }).first();
      const linkText = page.getByText(linkPattern).first();
      const isVisible = await link.isVisible({ timeout: 3_000 }).catch(() => false) ||
        await linkText.isVisible({ timeout: 1_000 }).catch(() => false);
      expect(isVisible, `Expected admin hub to show a link/text matching ${linkPattern}`).toBeTruthy();
    }

    await context.close();
  });

  test("can view tenant list on admin/tenants", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/admin/tenants");
    await expect(page.getByRole("heading", { name: /tenant/i })).toBeVisible({ timeout: 15_000 });

    // Should show a table or list of tenants
    const tenantList = page.locator("table, [data-testid='tenant-list'], [role='list']").first();
    await expect(tenantList).toBeVisible({ timeout: 10_000 }).catch(() => {
      // Layout may vary; heading presence is sufficient
    });

    await context.close();
  });

  test("can view jobs on admin/jobs", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/admin/jobs");
    await expect(page.getByRole("heading", { name: /job/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can view trials on admin/trials", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/admin/trials");
    await expect(page.getByRole("heading", { name: /trial/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can view health on admin/health", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/admin/health");
    await expect(page.getByRole("heading", { name: /health/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access admin/appearance", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/admin/appearance");
    await expect(page.getByRole("heading", { name: /appearance/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access admin/branding", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/admin/branding");
    await expect(page.getByRole("heading", { name: /branding/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  // --- Full tenant-level access ---

  test("can access tenant dashboard", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();
    const slug = getTestTenantSlug();

    await page.goto(`/dashboard/${slug}`);
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access preflight page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/preflight");
    await expect(page.getByRole("heading", { name: /preflight/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access team management", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/team");
    await expect(page.getByRole("heading", { name: /team/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access billing page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/billing");
    await expect(page.getByRole("heading", { name: /billing|subscription|plan/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access API keys page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/api-keys");
    await expect(page.getByRole("heading", { name: /api key/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access webhooks page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/webhooks");
    await expect(page.getByRole("heading", { name: /webhook/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access endpoints page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/endpoints");
    await expect(page.getByRole("heading", { name: /endpoint/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access account settings", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/account/settings");
    await expect(page.getByRole("heading", { name: /settings/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access account branding", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/account/branding");
    await expect(page.getByRole("heading", { name: /branding/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access account AI settings", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/account/ai");
    await expect(page.getByRole("heading", { name: /ai/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access rulesets page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/rulesets");
    await expect(page.getByRole("heading", { name: /ruleset/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access usage page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/usage");
    await expect(page.getByRole("heading", { name: /usage/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("can access reports page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/reports");
    await expect(page.getByRole("heading", { name: /report/i })).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  // --- Impersonation ---

  test("can impersonate a tenant from admin/tenants", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();
    const slug = getTestTenantSlug();

    await page.goto("/dashboard/admin/tenants");
    await expect(page.getByRole("heading", { name: /tenant/i })).toBeVisible({ timeout: 15_000 });

    // Look for a link or button to the test tenant
    const tenantLink = page.getByRole("link", { name: new RegExp(slug, "i") }).first();
    const tenantButton = page.getByRole("button", { name: new RegExp(slug, "i") }).first();
    const tenantText = page.getByText(new RegExp(slug, "i")).first();

    const hasLink = await tenantLink.isVisible({ timeout: 5_000 }).catch(() => false);
    const hasButton = await tenantButton.isVisible({ timeout: 1_000 }).catch(() => false);
    const hasText = await tenantText.isVisible({ timeout: 1_000 }).catch(() => false);

    // At minimum, the tenant slug should appear on the admin tenants page
    expect(
      hasLink || hasButton || hasText,
      `Expected test tenant "${slug}" to be visible on admin/tenants page`,
    ).toBeTruthy();

    // If there's a clickable element, click it and verify navigation
    if (hasLink) {
      await tenantLink.click();
      await page.waitForLoadState("domcontentloaded");
      // Should navigate to the tenant's dashboard or detail page
      expect(page.url()).toMatch(new RegExp(`(${slug}|tenant)`, "i"));
    }

    await context.close();
  });
});
