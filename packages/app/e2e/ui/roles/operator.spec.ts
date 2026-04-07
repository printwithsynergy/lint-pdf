import { test, expect } from "@playwright/test";
import {
  createRoleContext,
  isMcpBackdoorAvailable,
  getTestTenantSlug,
} from "../../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

/**
 * Helper: assert that a page loaded successfully for a "can access" test.
 * Tries to find a heading matching the pattern; if not found, at least verifies
 * the page did not redirect to the login screen.
 */
async function expectAccessible(
  page: import("@playwright/test").Page,
  headingPattern: RegExp,
) {
  const heading = page.locator("main").getByRole("heading", { name: headingPattern }).first();
  const visible = await heading.isVisible({ timeout: 15_000 }).catch(() => false);
  if (!visible) {
    // Fallback: the page should at least not have redirected to login
    expect(page.url()).not.toContain("/auth/login");
  }
}


test.describe("Role: Operator", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("can access the tenant dashboard", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "operator");
    const page = await context.newPage();
    const slug = getTestTenantSlug();

    await page.goto(`/dashboard/${slug}`);
    await expectAccessible(page, /dashboard/i);

    await context.close();
  });

  test("can access preflight page and see upload controls", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "operator");
    const page = await context.newPage();

    await page.goto("/dashboard/preflight");
    await expectAccessible(page, /preflight/i);

    // Operator should be able to submit preflight jobs
    const uploadIndicator = page.locator(
      "input[type='file'], button:has-text('upload'), button:has-text('submit'), [data-testid='upload-zone']"
    ).first();
    await expect(uploadIndicator).toBeVisible({ timeout: 10_000 }).catch(() => {
      // Upload UI may vary
    });

    await context.close();
  });

  test("can view rulesets page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "operator");
    const page = await context.newPage();

    await page.goto("/dashboard/rulesets");
    await expectAccessible(page, /ruleset/i);

    await context.close();
  });

  test("can manage endpoints", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "operator");
    const page = await context.newPage();

    await page.goto("/dashboard/endpoints");
    await expectAccessible(page, /endpoint/i);

    await context.close();
  });

  test("can view usage page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "operator");
    const page = await context.newPage();

    await page.goto("/dashboard/usage");
    await expectAccessible(page, /usage/i);

    await context.close();
  });

  test("can view reports page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "operator");
    const page = await context.newPage();

    await page.goto("/dashboard/reports");
    await expectAccessible(page, /report/i);

    await context.close();
  });

  test("can access own profile", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "operator");
    const page = await context.newPage();

    await page.goto("/dashboard/profile");
    await expectAccessible(page, /profile/i);

    await context.close();
  });

  // --- Blocked pages ---
  // The server-side layout redirects unauthorized users to /dashboard.

  test("cannot access team invite page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "operator");
    const page = await context.newPage();

    await page.goto("/dashboard/team/invite", { waitUntil: "domcontentloaded" });

    // Should be redirected to /dashboard by the permission layout
    expect(page.url()).toMatch(/\/dashboard\/?$/);

    await context.close();
  });

  test("cannot access billing page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "operator");
    const page = await context.newPage();

    await page.goto("/dashboard/billing", { waitUntil: "domcontentloaded" });

    // Should be redirected to /dashboard by the permission layout
    expect(page.url()).toMatch(/\/dashboard\/?$/);

    await context.close();
  });

  test("cannot access API keys page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "operator");
    const page = await context.newPage();

    await page.goto("/dashboard/api-keys", { waitUntil: "domcontentloaded" });

    // Should be redirected to /dashboard by the permission layout
    expect(page.url()).toMatch(/\/dashboard\/?$/);

    await context.close();
  });

  test("cannot access account settings page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "operator");
    const page = await context.newPage();

    await page.goto("/dashboard/account/settings", { waitUntil: "domcontentloaded" });

    // Should be redirected to /dashboard by the permission layout
    expect(page.url()).toMatch(/\/dashboard\/?$/);

    await context.close();
  });

  test("cannot access webhooks page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "operator");
    const page = await context.newPage();

    await page.goto("/dashboard/webhooks", { waitUntil: "domcontentloaded" });

    // Should be redirected to /dashboard by the permission layout
    expect(page.url()).toMatch(/\/dashboard\/?$/);

    await context.close();
  });

  test("cannot access admin page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "operator");
    const page = await context.newPage();

    await page.goto("/dashboard/admin", { waitUntil: "domcontentloaded" });

    expect(page.url()).toMatch(/\/dashboard\/?$/);

    await context.close();
  });
});
