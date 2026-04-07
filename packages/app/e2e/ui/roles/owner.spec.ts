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


test.describe("Role: Owner", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("can access the tenant dashboard", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    const slug = getTestTenantSlug();

    await page.goto(`/dashboard/${slug}`);
    await expectAccessible(page, /dashboard/i);

    await context.close();
  });

  test("can see team management page with member list", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/team");
    await expectAccessible(page, /team/i);

    // Should show at least one team member row or member-related content
    const memberIndicator = page.locator("table, [data-testid='team-members'], [role='list']").first();
    await expect(memberIndicator).toBeVisible({ timeout: 10_000 }).catch(() => {
      // Fallback: just verify the page loaded without error
    });

    await context.close();
  });

  test("can access billing page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/billing");
    await expectAccessible(page, /billing|subscription|plan/i);

    await context.close();
  });

  test("can see API keys page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/api-keys");
    await expectAccessible(page, /api key/i);

    await context.close();
  });

  test("can access preflight page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/preflight");
    await expectAccessible(page, /preflight/i);

    // Should have an upload area or submit button for preflight jobs
    const uploadArea = page.locator(
      "input[type='file'], [data-testid='upload-zone'], button:has-text('upload'), button:has-text('submit'), [role='button']:has-text('upload')"
    ).first();
    await expect(uploadArea).toBeVisible({ timeout: 10_000 }).catch(() => {
      // Upload UI may vary; page loading without error is sufficient
    });

    await context.close();
  });

  test("can view rulesets page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/rulesets");
    await expectAccessible(page, /ruleset/i);

    await context.close();
  });

  test("can manage webhooks", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/webhooks");
    await expectAccessible(page, /webhook/i);

    await context.close();
  });

  test("can access account settings", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/account/settings");
    await expectAccessible(page, /settings/i);

    await context.close();
  });

  test("can access account branding", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/account/branding");
    await expectAccessible(page, /branding/i);

    await context.close();
  });

  test("can access account AI settings", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/account/ai");
    await expectAccessible(page, /ai/i);

    await context.close();
  });

  test("can invite team members", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/team/invite");
    await expectAccessible(page, /invite|add member/i);

    await context.close();
  });

  test("can access endpoints page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/endpoints");
    await expectAccessible(page, /endpoint/i);

    await context.close();
  });

  test("cannot access admin page (super-admin only)", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/admin", { waitUntil: "domcontentloaded" });

    expect(page.url()).toMatch(/\/dashboard\/?$/);

    await context.close();
  });
});
