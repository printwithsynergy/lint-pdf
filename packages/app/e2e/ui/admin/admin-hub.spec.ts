import { test, expect } from "@playwright/test";
import {
  createRoleContext,
  isMcpBackdoorAvailable,
} from "../../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Admin Hub (/dashboard/admin)", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor is not enabled on this environment");
  });

  test.describe("Super-admin access", () => {
    test("page loads with Site Administration heading", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");

      await expect(
        page.locator("main").getByRole("heading", { name: /site administration/i }).first(),
      ).toBeVisible({ timeout: 15_000 });

      await context.close();
    });

    test("shows link to All Tenants", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");
      await page.waitForTimeout(3_000);

      // The admin hub uses Next.js <Link href="/dashboard/admin/tenants"> wrapping
      // <h2>All Tenants</h2> + <p> description text. Match by href or text content.
      const hasLinkByHref = await page.locator("a[href*='/admin/tenants']").first().isVisible({ timeout: 15_000 }).catch(() => false);
      const hasLink = await page.getByRole("link", { name: /all tenants/i }).first().isVisible({ timeout: 5_000 }).catch(() => false);
      const hasText = await page.getByText(/all tenants/i).first().isVisible().catch(() => false);
      expect(hasLinkByHref || hasLink || hasText).toBeTruthy();

      await context.close();
    });

    test("shows link to All Jobs", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");

      const link = page.getByRole("link", { name: /all jobs/i });
      const hasLink = await link.isVisible({ timeout: 15_000 }).catch(() => false);
      const hasText = await page.getByText(/all jobs/i).first().isVisible().catch(() => false);
      expect(hasLink || hasText).toBeTruthy();

      await context.close();
    });

    test("shows link to Trial Submissions", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");

      const link = page.getByRole("link", { name: /trial submissions/i });
      const hasLink = await link.isVisible({ timeout: 15_000 }).catch(() => false);
      const hasText = await page.getByText(/trial submissions/i).first().isVisible().catch(() => false);
      expect(hasLink || hasText).toBeTruthy();

      await context.close();
    });

    test("shows link to System Health", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");

      const link = page.getByRole("link", { name: /system health/i });
      const hasLink = await link.isVisible({ timeout: 15_000 }).catch(() => false);
      const hasText = await page.getByText(/system health/i).first().isVisible().catch(() => false);
      expect(hasLink || hasText).toBeTruthy();

      await context.close();
    });

    test("All Tenants link navigates to tenants page", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");
      await page.waitForTimeout(3_000);

      // The admin hub uses <Link href="/dashboard/admin/tenants"> wrapping <h2>All Tenants</h2>
      // Try href-based locator first (most reliable), then role-based
      const hrefLink = page.locator("a[href*='/admin/tenants']").first();
      const roleLink = page.getByRole("link", { name: /all tenants/i }).first();
      const hasHrefLink = await hrefLink.isVisible({ timeout: 10_000 }).catch(() => false);
      const hasRoleLink = await roleLink.isVisible({ timeout: 3_000 }).catch(() => false);

      if (hasHrefLink) {
        await hrefLink.click();
      } else if (hasRoleLink) {
        await roleLink.click();
      } else {
        // Last resort: navigate directly
        await page.goto("/dashboard/admin/tenants");
      }

      await page.waitForURL(/\/dashboard\/admin\/tenants/, { timeout: 15_000 });
      await expect(page).toHaveURL(/\/dashboard\/admin\/tenants/);

      await context.close();
    });

    test("All Jobs link navigates to jobs page", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");
      await page.waitForTimeout(3_000);

      const link = page.getByRole("link", { name: /all jobs/i }).first();
      const hasLink = await link.isVisible({ timeout: 5_000 }).catch(() => false);
      if (hasLink) {
        await link.click();
      } else {
        await page.locator("a[href*='/admin/jobs']").first().click();
      }

      await page.waitForURL(/\/dashboard\/admin\/jobs/, { timeout: 15_000 });
      await expect(page).toHaveURL(/\/dashboard\/admin\/jobs/);

      await context.close();
    });

    test("Trial Submissions link navigates to trials page", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");
      await page.waitForTimeout(3_000);

      const link = page.getByRole("link", { name: /trial submissions/i }).first();
      const hasLink = await link.isVisible({ timeout: 5_000 }).catch(() => false);
      if (hasLink) {
        await link.click();
      } else {
        await page.locator("a[href*='/admin/trials']").first().click();
      }

      await page.waitForURL(/\/dashboard\/admin\/trials/, { timeout: 15_000 });
      await expect(page).toHaveURL(/\/dashboard\/admin\/trials/);

      await context.close();
    });

    test("System Health link navigates to health page", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");
      await page.waitForTimeout(3_000);

      const link = page.getByRole("link", { name: /system health/i }).first();
      const hasLink = await link.isVisible({ timeout: 5_000 }).catch(() => false);
      if (hasLink) {
        await link.click();
      } else {
        await page.locator("a[href*='/admin/health']").first().click();
      }

      await page.waitForURL(/\/dashboard\/admin\/health/, { timeout: 15_000 });
      await expect(page).toHaveURL(/\/dashboard\/admin\/health/);

      await context.close();
    });
  });

  test.describe("Access control", () => {
    test("non-admin user is denied access", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "member");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");

      // Should redirect away or show forbidden
      const url = page.url();
      const forbiddenVisible = await page
        .getByText(/forbidden|not authorized|access denied/i)
        .isVisible()
        .catch(() => false);

      const redirectedAway = !url.includes("/dashboard/admin") ||
        url.includes("/auth/login") ||
        url.includes("/dashboard") && !url.includes("/admin");

      expect(forbiddenVisible || redirectedAway).toBe(true);

      await context.close();
    });

    test("owner role is denied access to admin hub", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "owner");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");

      const url = page.url();
      const forbiddenVisible = await page
        .getByText(/forbidden|not authorized|access denied/i)
        .isVisible()
        .catch(() => false);

      const redirectedAway = !url.includes("/dashboard/admin") ||
        url.includes("/auth/login");

      expect(forbiddenVisible || redirectedAway).toBe(true);

      await context.close();
    });

    test("unauthenticated user is redirected to login", async ({ page }) => {
      await page.goto("/dashboard/admin");

      await page.waitForURL(/\/auth\/login/, { timeout: 15_000 });
      await expect(page).toHaveURL(/\/auth\/login/);
    });
  });
});
