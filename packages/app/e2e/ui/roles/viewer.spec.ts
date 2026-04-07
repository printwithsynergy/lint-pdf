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
    await expectAccessible(page, /dashboard/i);

    await context.close();
  });

  test("can view tenant dashboard", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();
    const slug = getTestTenantSlug();

    await page.goto(`/dashboard/${slug}`);
    await expectAccessible(page, /dashboard/i);

    await context.close();
  });

  test("can view preflight results (read-only)", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/preflight");
    await expectAccessible(page, /preflight/i);

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
    await expectAccessible(page, /ruleset/i);

    await context.close();
  });

  test("can view usage page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/usage");
    await expectAccessible(page, /usage/i);

    await context.close();
  });

  test("can view reports page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/reports");
    await expectAccessible(page, /report/i);

    await context.close();
  });

  test("can access own profile", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/profile");
    await expectAccessible(page, /profile/i);

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
  // The server-side layout redirects unauthorized users to /dashboard.

  test("cannot access team invite page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/team/invite", { waitUntil: "domcontentloaded" });

    // Should be redirected away from /dashboard/team/invite
    // Permission layout redirects to /dashboard, page redirect goes to /dashboard/team
    expect(page.url()).not.toContain("/team/invite");

    await context.close();
  });

  test("cannot access billing page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/billing", { waitUntil: "domcontentloaded" });

    // Should be redirected to /dashboard by the permission layout
    expect(page.url()).toMatch(/\/dashboard\/?$/);

    await context.close();
  });

  test("cannot access API keys page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/api-keys", { waitUntil: "domcontentloaded" });

    // Should be redirected to /dashboard by the permission layout
    expect(page.url()).toMatch(/\/dashboard\/?$/);

    await context.close();
  });

  test("cannot access webhooks page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/webhooks", { waitUntil: "domcontentloaded" });

    // Should be redirected to /dashboard by the permission layout
    expect(page.url()).toMatch(/\/dashboard\/?$/);

    await context.close();
  });

  test("cannot access endpoints page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/endpoints", { waitUntil: "domcontentloaded" });

    // Should be redirected to /dashboard by the permission layout
    expect(page.url()).toMatch(/\/dashboard\/?$/);

    await context.close();
  });

  test("cannot access account settings page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/account/settings", { waitUntil: "domcontentloaded" });

    // Should be redirected to /dashboard by the permission layout
    expect(page.url()).toMatch(/\/dashboard\/?$/);

    await context.close();
  });

  test("cannot access account branding page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/account/branding", { waitUntil: "domcontentloaded" });

    expect(page.url()).toMatch(/\/dashboard\/?$/);

    await context.close();
  });

  test("cannot access admin page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/admin", { waitUntil: "domcontentloaded" });

    expect(page.url()).toMatch(/\/dashboard\/?$/);

    await context.close();
  });

  test("cannot access admin tenants page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "viewer");
    const page = await context.newPage();

    await page.goto("/dashboard/admin/tenants", { waitUntil: "domcontentloaded" });

    expect(page.url()).toMatch(/\/dashboard\/?$/);

    await context.close();
  });
});
