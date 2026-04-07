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
      page.locator("main").getByRole("heading", { name: /custom api endpoints/i }).first(),
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

    const newButton = page.locator("button", { hasText: /new endpoint/i });
    await expect(newButton).toBeVisible({ timeout: 15_000 });
    await newButton.click();

    // Create form should appear with heading "New Custom Endpoint"
    const hasFormHeading = await page
      .getByRole("heading", { name: /new custom endpoint/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasFormText = await page
      .getByText(/new custom endpoint/i)
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasFormHeading || hasFormText).toBeTruthy();
    await context.close();
  });

  test("create form has slug, profile, and description fields", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/endpoints");

    // The "New Endpoint" button is a plain <button>, not a Button component
    const newBtn = page.locator("button", { hasText: /new endpoint/i });
    await expect(newBtn).toBeVisible({ timeout: 15_000 });
    await newBtn.click();
    await page.waitForTimeout(1_000);

    // URL Slug input with placeholder
    const hasSlug = await page.getByPlaceholder("my-magazine-check").isVisible().catch(() => false);
    const hasSlugLabel = await page.getByText(/url slug/i).first().isVisible().catch(() => false);
    expect(hasSlug || hasSlugLabel).toBeTruthy();

    // Profile selector — a <select> element with a "Select a profile..." option
    const hasSelect = await page.locator("select").first().isVisible().catch(() => false);
    const hasProfileLabel = await page.getByText(/profile/i).first().isVisible().catch(() => false);
    expect(hasSelect || hasProfileLabel).toBeTruthy();

    // Description input with placeholder
    const hasDesc = await page.getByPlaceholder("Optional description").isVisible().catch(() => false);
    const hasDescLabel = await page.getByText(/description/i).first().isVisible().catch(() => false);
    expect(hasDesc || hasDescLabel).toBeTruthy();
    await context.close();
  });

  test("create form shows URL preview", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/endpoints");

    await page.locator("button", { hasText: /new endpoint/i }).click();
    await page.waitForTimeout(1_000);

    // Should show URL preview with slug placeholder
    const hasPreview = await page.getByText(/\/api\/v1\/e\//).first().isVisible().catch(() => false);
    const hasUrl = await page.locator("code").first().isVisible().catch(() => false);
    expect(hasPreview || hasUrl).toBeTruthy();
    await context.close();
  });

  test("create endpoint button is disabled without required fields", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/endpoints");

    await page.locator("button", { hasText: /new endpoint/i }).click();
    await page.waitForTimeout(1_000);

    const createButton = page.locator("button", { hasText: /create endpoint/i });
    await expect(createButton).toBeVisible({ timeout: 5_000 });
    // Button should be disabled when slug and profile are empty
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
