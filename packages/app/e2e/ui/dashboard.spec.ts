import { test, expect } from "@playwright/test";
import { createAuthenticatedContext, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Dashboard", () => {
  test("redirects to login when not authenticated", async ({ page }) => {
    await page.goto("/dashboard");

    // Should redirect to login page
    await page.waitForURL(/\/auth\/login/, { timeout: 15_000 });
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test.describe("Authenticated", () => {
    test.beforeAll(async ({ request }) => {
      const available = await isMcpBackdoorAvailable(request);
      test.skip(!available, "MCP backdoor is not enabled on this environment");
    });

    test("shows dashboard when authenticated", async ({ browser }) => {
      const { context } = await createAuthenticatedContext(browser, APP_BASE);
      const page = await context.newPage();

      await page.goto("/dashboard");

      // Should show dashboard heading
      await expect(
        page.locator("main").getByRole("heading", { name: /dashboard/i }).first(),
      ).toBeVisible({ timeout: 15_000 });

      await context.close();
    });

    test("shows welcome message with user info", async ({ browser }) => {
      const { context } = await createAuthenticatedContext(browser, APP_BASE);
      const page = await context.newPage();

      await page.goto("/dashboard");

      // Should show welcome back message
      await expect(page.getByText(/welcome back/i)).toBeVisible({
        timeout: 15_000,
      });

      await context.close();
    });

    test("shows organizations section", async ({ browser }) => {
      const { context } = await createAuthenticatedContext(browser, APP_BASE);
      const page = await context.newPage();

      await page.goto("/dashboard");

      await expect(
        page.locator("main").getByRole("heading", { name: /your organizations/i }).first(),
      ).toBeVisible({ timeout: 15_000 });

      await context.close();
    });

    test("has sign out link", async ({ browser }) => {
      const { context } = await createAuthenticatedContext(browser, APP_BASE);
      const page = await context.newPage();

      await page.goto("/dashboard");

      await expect(page.getByRole("link", { name: /sign out/i })).toBeVisible({
        timeout: 15_000,
      });

      await context.close();
    });
  });
});
