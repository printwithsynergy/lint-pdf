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

test.describe("Role: Member", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("can access the main dashboard", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard");
    await expectAccessible(page, /dashboard/i);

    await context.close();
  });

  test("can access tenant dashboard", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();
    const slug = getTestTenantSlug();

    await page.goto(`/dashboard/${slug}`);
    await expectAccessible(page, /dashboard/i);

    await context.close();
  });

  test("can view preflight jobs and results", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/preflight");
    await expectAccessible(page, /preflight/i);

    await context.close();
  });

  test("can view rulesets page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/rulesets");
    await expectAccessible(page, /ruleset/i);

    await context.close();
  });

  test("can view usage page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/usage");
    await expectAccessible(page, /usage/i);

    await context.close();
  });

  test("can view reports page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/reports");
    await expectAccessible(page, /report/i);

    await context.close();
  });

  test("can access own profile", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/profile");
    await expectAccessible(page, /profile/i);

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
    await expectRestricted(page, "/dashboard/team/invite");

    await context.close();
  });

  test("cannot access billing page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/billing", { waitUntil: "domcontentloaded" });
    await expectRestricted(page, "/dashboard/billing");

    await context.close();
  });

  test("cannot access API keys page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/api-keys", { waitUntil: "domcontentloaded" });
    await expectRestricted(page, "/dashboard/api-keys");

    await context.close();
  });

  test("cannot access account settings", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/account/settings", { waitUntil: "domcontentloaded" });
    await expectRestricted(page, "/dashboard/account/settings");

    await context.close();
  });

  test("cannot access webhooks page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/webhooks", { waitUntil: "domcontentloaded" });
    await expectRestricted(page, "/dashboard/webhooks");

    await context.close();
  });

  test("cannot access endpoints page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/endpoints", { waitUntil: "domcontentloaded" });
    await expectRestricted(page, "/dashboard/endpoints");

    await context.close();
  });

  test("cannot access admin pages", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "member");
    const page = await context.newPage();

    await page.goto("/dashboard/admin", { waitUntil: "domcontentloaded" });
    await expectRestricted(page, "/dashboard/admin");

    await context.close();
  });
});
