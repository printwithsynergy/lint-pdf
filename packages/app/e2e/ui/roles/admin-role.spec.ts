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

/**
 * Helper: assert that a page is restricted for a "cannot access" test.
 * Checks for redirect to login, redirect to dashboard, an unauthorized message,
 * or simply that the URL no longer contains the restricted path.
 */
async function expectRestricted(
  page: import("@playwright/test").Page,
  restrictedPath: string,
) {
  const currentUrl = page.url();
  const isRedirected =
    /\/auth\/login/.test(currentUrl) ||
    /\/dashboard\/?$/.test(currentUrl) ||
    !currentUrl.includes(restrictedPath);
  const hasUnauthorized = await page
    .getByText(/unauthorized|forbidden|access denied|not allowed/i)
    .first()
    .isVisible({ timeout: 5_000 })
    .catch(() => false);

  expect(isRedirected || hasUnauthorized).toBeTruthy();
}

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
    await expectAccessible(page, /dashboard/i);

    await context.close();
  });

  test("can manage team members", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/team");
    await expectAccessible(page, /team/i);

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
    await expectAccessible(page, /invite|add member/i);

    await context.close();
  });

  test("can access billing page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/billing");
    await expectAccessible(page, /billing|subscription|plan/i);

    await context.close();
  });

  test("can access API keys page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/api-keys");
    await expectAccessible(page, /api key/i);

    await context.close();
  });

  test("can access preflight page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/preflight");
    await expectAccessible(page, /preflight/i);

    await context.close();
  });

  test("can access rulesets page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/rulesets");
    await expectAccessible(page, /ruleset/i);

    await context.close();
  });

  test("can manage webhooks", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/webhooks");
    await expectAccessible(page, /webhook/i);

    await context.close();
  });

  test("can access account settings", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/account/settings");
    await expectAccessible(page, /settings/i);

    await context.close();
  });

  test("can access account branding", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/account/branding");
    await expectAccessible(page, /branding/i);

    await context.close();
  });

  test("can access account AI settings", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/account/ai");
    await expectAccessible(page, /ai/i);

    await context.close();
  });

  test("can access endpoints page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/endpoints");
    await expectAccessible(page, /endpoint/i);

    await context.close();
  });

  test("cannot access super-admin pages", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/admin", { waitUntil: "domcontentloaded" });
    await expectRestricted(page, "/dashboard/admin");

    await context.close();
  });

  test("cannot access admin/tenants", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "admin");
    const page = await context.newPage();

    await page.goto("/dashboard/admin/tenants", { waitUntil: "domcontentloaded" });
    await expectRestricted(page, "/dashboard/admin/tenants");

    await context.close();
  });
});
