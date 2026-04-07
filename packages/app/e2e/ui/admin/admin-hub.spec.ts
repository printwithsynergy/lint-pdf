import { test, expect } from "@playwright/test";
import {
  createRoleContext,
  createAuthenticatedContext,
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
        page.getByRole("heading", { name: /site administration/i }),
      ).toBeVisible({ timeout: 15_000 });

      await context.close();
    });

    test("shows link to All Tenants", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");

      const link = page.getByRole("link", { name: /all tenants/i });
      await expect(link).toBeVisible({ timeout: 15_000 });

      await context.close();
    });

    test("shows link to All Jobs", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");

      const link = page.getByRole("link", { name: /all jobs/i });
      await expect(link).toBeVisible({ timeout: 15_000 });

      await context.close();
    });

    test("shows link to Trial Submissions", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");

      const link = page.getByRole("link", { name: /trial submissions/i });
      await expect(link).toBeVisible({ timeout: 15_000 });

      await context.close();
    });

    test("shows link to System Health", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");

      const link = page.getByRole("link", { name: /system health/i });
      await expect(link).toBeVisible({ timeout: 15_000 });

      await context.close();
    });

    test("All Tenants link navigates to tenants page", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");
      await page.getByRole("link", { name: /all tenants/i }).click();

      await page.waitForURL(/\/dashboard\/admin\/tenants/, { timeout: 15_000 });
      await expect(page).toHaveURL(/\/dashboard\/admin\/tenants/);

      await context.close();
    });

    test("All Jobs link navigates to jobs page", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");
      await page.getByRole("link", { name: /all jobs/i }).click();

      await page.waitForURL(/\/dashboard\/admin\/jobs/, { timeout: 15_000 });
      await expect(page).toHaveURL(/\/dashboard\/admin\/jobs/);

      await context.close();
    });

    test("Trial Submissions link navigates to trials page", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");
      await page.getByRole("link", { name: /trial submissions/i }).click();

      await page.waitForURL(/\/dashboard\/admin\/trials/, { timeout: 15_000 });
      await expect(page).toHaveURL(/\/dashboard\/admin\/trials/);

      await context.close();
    });

    test("System Health link navigates to health page", async ({ browser }) => {
      const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
      const page = await context.newPage();

      await page.goto("/dashboard/admin");
      await page.getByRole("link", { name: /system health/i }).click();

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
