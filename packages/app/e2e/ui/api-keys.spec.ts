import { test, expect } from "@playwright/test";
import { createRoleContext, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("API Keys Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("page loads with heading", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/api-keys");
    await expect(
      page.getByRole("heading", { name: /api keys/i }),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows description text", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/api-keys");
    await expect(
      page.getByText(/manage api keys for authenticating/i),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows existing keys or empty state", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/api-keys");
    await page.waitForTimeout(3_000);

    // Either keys are listed or empty state is shown
    const hasKeys = await page.getByRole("button", { name: /revoke/i }).first().isVisible().catch(() => false);
    if (!hasKeys) {
      await expect(page.getByText(/no api keys/i)).toBeVisible({ timeout: 15_000 });
      await expect(
        page.getByText(/create one to authenticate/i),
      ).toBeVisible();
    }
    await context.close();
  });

  test("create key button exists", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/api-keys");

    const createButton = page.getByRole("button", { name: /create key/i }).first();
    await expect(createButton).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("clicking create key shows form with label input", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/api-keys");

    const createButton = page.getByRole("button", { name: /create key/i }).first();
    await expect(createButton).toBeVisible({ timeout: 15_000 });
    await createButton.click();

    // Create form should appear
    await expect(
      page.getByRole("heading", { name: /new api key/i }),
    ).toBeVisible({ timeout: 5_000 });
    await expect(page.locator("#key-label")).toBeVisible();
    await context.close();
  });

  test("create form has create button", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/api-keys");

    await page.getByRole("button", { name: /create key/i }).first().click();
    await page.waitForTimeout(1_000);

    // There should be a Create button inside the form
    const formCreateButton = page.getByRole("button", { name: /^create$/i });
    await expect(formCreateButton).toBeVisible({ timeout: 5_000 });
    await context.close();
  });

  test("existing keys show prefix and revoke button", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/api-keys");
    await page.waitForTimeout(3_000);

    const revokeButton = page.getByRole("button", { name: /revoke/i }).first();
    const hasKeys = await revokeButton.isVisible().catch(() => false);
    if (hasKeys) {
      await expect(revokeButton).toBeVisible();
      // Keys show prefix with ellipsis
      await expect(page.getByText(/\.\.\./)).toBeVisible();
      // Should show created date
      await expect(page.getByText(/created/i).first()).toBeVisible();
    }
    await context.close();
  });

  test("revoke button opens confirm dialog", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/api-keys");
    await page.waitForTimeout(3_000);

    const revokeButton = page.getByRole("button", { name: /revoke/i }).first();
    const hasKeys = await revokeButton.isVisible().catch(() => false);
    if (hasKeys) {
      await revokeButton.click();
      await expect(page.getByText(/revoke api key\?/i)).toBeVisible({ timeout: 5_000 });
      await expect(page.getByText(/this action cannot be undone/i)).toBeVisible();
      await expect(
        page.getByText(/any integrations using this key will stop working/i),
      ).toBeVisible();
    }
    await context.close();
  });
});
