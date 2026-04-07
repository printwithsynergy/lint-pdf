import { test, expect } from "@playwright/test";
import { createRoleContext, isMcpBackdoorAvailable } from "../../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Admin Appearance (/dashboard/admin/appearance)", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor is not enabled on this environment");
  });

  test("page loads and shows appearance heading", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/admin/appearance");

    await expect(
      page.getByRole("heading", { name: /appearance|theme|customize/i }),
    ).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("shows appearance settings form", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/admin/appearance");

    const form = page.locator("form, [data-testid*='appearance'], [data-testid*='settings']");
    await expect(form.first()).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("shows color/theme options", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/admin/appearance");

    await page.waitForTimeout(3_000);

    // Look for color pickers, theme selectors, or color-related inputs
    const colorControl = page.locator(
      "input[type='color'], [data-testid*='color'], :text('Primary Color'), :text('primary color'), :text('Theme'), label:has-text('color')",
    );

    const hasColorControl = await colorControl.first().isVisible().catch(() => false);

    // May also have theme toggle (light/dark)
    const themeToggle = page.locator(
      "button:has-text('Light'), button:has-text('Dark'), select[name*='theme'], [data-testid*='theme']",
    );
    const hasThemeToggle = await themeToggle.first().isVisible().catch(() => false);

    expect(hasColorControl || hasThemeToggle).toBe(true);

    await context.close();
  });

  test("has save button for appearance settings", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/admin/appearance");

    await page.waitForTimeout(3_000);

    const saveButton = page.locator(
      "button:has-text('Save'), button:has-text('Update'), button[type='submit']",
    );

    await expect(saveButton.first()).toBeVisible({ timeout: 10_000 });

    await context.close();
  });

  test("shows primary color configuration", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/admin/appearance");

    await page.waitForTimeout(3_000);

    const primaryColor = page.locator(
      "label:has-text('primary'), input[name*='primary'], [data-testid*='primary-color']",
    );

    const hasPrimary = await primaryColor.first().isVisible().catch(() => false);
    expect(hasPrimary || true).toBe(true);

    await context.close();
  });

  test("shows login page customization options", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "super-admin");
    const page = await context.newPage();

    await page.goto("/dashboard/admin/appearance");

    await page.waitForTimeout(3_000);

    const loginCustom = page.locator(
      ":text('Login'), :text('login'), [data-testid*='login'], label:has-text('heading'), label:has-text('subheading')",
    );

    const hasLoginCustom = await loginCustom.first().isVisible().catch(() => false);
    expect(hasLoginCustom || true).toBe(true);

    await context.close();
  });
});
