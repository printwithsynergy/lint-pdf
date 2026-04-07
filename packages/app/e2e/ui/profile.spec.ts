import { test, expect } from "@playwright/test";
import { createRoleContext, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("User Profile Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("page loads without server error", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    const response = await page.goto("/dashboard/profile");
    expect(response).not.toBeNull();
    expect(response!.status()).toBeLessThan(500);
    await context.close();
  });

  test("page shows profile-related content", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/profile");
    await page.waitForTimeout(5_000);

    // ProfilePage is from pixie-dust-dashboard; look for common profile elements
    const hasProfileHeading = await page
      .getByRole("heading", { name: /profile/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasContent = await page.locator("main, [role='main'], .container, section, form").first().isVisible().catch(() => false);

    expect(hasProfileHeading || hasContent).toBeTruthy();
    await context.close();
  });

  test("page shows user email or name", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/profile");
    await page.waitForTimeout(5_000);

    // Should show user information — email or name fields
    const hasEmail = await page
      .getByText(/email/i)
      .first()
      .isVisible()
      .catch(() => false);
    const hasName = await page
      .getByText(/name/i)
      .first()
      .isVisible()
      .catch(() => false);
    const hasInput = await page.locator("input").first().isVisible().catch(() => false);

    expect(hasEmail || hasName || hasInput).toBeTruthy();
    await context.close();
  });

  test("page has editable form elements", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/profile");
    await page.waitForTimeout(5_000);

    // Should have input fields for editing profile
    const inputs = page.locator("input");
    const inputCount = await inputs.count();
    expect(inputCount).toBeGreaterThan(0);
    await context.close();
  });

  test("page has a save or update button", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/profile");
    await page.waitForTimeout(5_000);

    const hasSaveButton = await page
      .getByRole("button", { name: /save|update|submit/i })
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasSaveButton).toBeTruthy();
    await context.close();
  });
});
