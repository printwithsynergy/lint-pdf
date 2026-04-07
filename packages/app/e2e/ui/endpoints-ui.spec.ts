import { test, expect } from "@playwright/test";
import { createRoleContext, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Custom Endpoints Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("page loads with heading", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/endpoints");
    await expect(
      page.getByRole("heading", { name: /custom api endpoints/i }),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows description text", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/endpoints");
    await expect(
      page.getByText(/create vanity url slugs/i),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows existing endpoints or empty state", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/endpoints");
    await page.waitForTimeout(3_000);

    const editButton = page.getByRole("button", { name: /edit/i }).first();
    const hasEndpoints = await editButton.isVisible().catch(() => false);
    if (!hasEndpoints) {
      await expect(
        page.getByText(/no custom endpoints yet/i),
      ).toBeVisible({ timeout: 15_000 });
    }
    await context.close();
  });

  test("new endpoint button exists and toggles create form", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/endpoints");

    const newButton = page.getByRole("button", { name: /new endpoint/i });
    await expect(newButton).toBeVisible({ timeout: 15_000 });
    await newButton.click();

    // Create form should appear
    await expect(
      page.getByRole("heading", { name: /new custom endpoint/i }),
    ).toBeVisible({ timeout: 5_000 });
    await context.close();
  });

  test("create form has slug, profile, and description fields", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/endpoints");

    await page.getByRole("button", { name: /new endpoint/i }).click();
    await page.waitForTimeout(1_000);

    // URL Slug input
    await expect(page.getByPlaceholder("my-magazine-check")).toBeVisible({ timeout: 5_000 });
    // Profile selector
    await expect(page.getByText(/select a profile/i)).toBeVisible();
    // Description input
    await expect(page.getByPlaceholder("Optional description")).toBeVisible();
    await context.close();
  });

  test("create form shows URL preview", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/endpoints");

    await page.getByRole("button", { name: /new endpoint/i }).click();
    await page.waitForTimeout(1_000);

    // Should show URL preview with slug placeholder
    await expect(page.getByText(/\/api\/v1\/e\//)).toBeVisible({ timeout: 5_000 });
    await context.close();
  });

  test("create endpoint button is disabled without required fields", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/endpoints");

    await page.getByRole("button", { name: /new endpoint/i }).click();
    await page.waitForTimeout(1_000);

    const createButton = page.getByRole("button", { name: /create endpoint/i });
    await expect(createButton).toBeVisible({ timeout: 5_000 });
    await expect(createButton).toBeDisabled();
    await context.close();
  });

  test("existing endpoints show slug, profile, and action buttons", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/endpoints");
    await page.waitForTimeout(3_000);

    const editButton = page.getByRole("button", { name: /edit/i }).first();
    const hasEndpoints = await editButton.isVisible().catch(() => false);
    if (hasEndpoints) {
      // Should show endpoint slug
      await expect(page.getByText(/\/api\/v1\/e\//).first()).toBeVisible();
      // Should show profile info
      await expect(page.getByText(/profile:/i).first()).toBeVisible();
      // Action buttons
      await expect(editButton).toBeVisible();
      await expect(page.getByRole("button", { name: /disable|enable/i }).first()).toBeVisible();
      await expect(page.getByRole("button", { name: /delete/i }).first()).toBeVisible();
    }
    await context.close();
  });

  test("edit button opens inline edit form", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/endpoints");
    await page.waitForTimeout(3_000);

    const editButton = page.getByRole("button", { name: /edit/i }).first();
    const hasEndpoints = await editButton.isVisible().catch(() => false);
    if (hasEndpoints) {
      await editButton.click();
      await expect(page.getByRole("button", { name: /save/i })).toBeVisible({ timeout: 5_000 });
      await expect(page.getByRole("button", { name: /cancel/i })).toBeVisible();
    }
    await context.close();
  });
});
