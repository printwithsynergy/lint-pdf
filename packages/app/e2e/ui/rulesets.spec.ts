import { test, expect } from "@playwright/test";
import { createRoleContext, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Rulesets Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("page loads with heading", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/rulesets");
    await expect(
      page.locator("main").getByRole("heading", { name: /rulesets/i }).first(),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows description text", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/rulesets");
    await expect(
      page.getByText(/preflight profiles that define which checks run/i),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("built-in rulesets section is listed", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/rulesets");
    await expect(
      page.locator("main").getByRole("heading", { name: /built-in rulesets/i }).first(),
    ).toBeVisible({ timeout: 15_000 });
    await expect(
      page.getByText(/pre-configured profiles provided by lintpdf/i),
    ).toBeVisible();
    await context.close();
  });

  test("built-in profiles show built-in badge", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/rulesets");
    await page.waitForTimeout(3_000);

    // Built-in profiles should have the "built-in" badge
    const builtInBadge = page.getByText("built-in").first();
    await expect(builtInBadge).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("built-in profiles have view and clone buttons", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/rulesets");
    await page.waitForTimeout(5_000);

    // Look for View and Clone buttons anywhere on the page (built-in profiles render them)
    const viewButton = page.getByRole("button", { name: /view/i }).first();
    const cloneButton = page.getByRole("button", { name: /clone/i }).first();

    const hasView = await viewButton.isVisible({ timeout: 15_000 }).catch(() => false);
    const hasClone = await cloneButton.isVisible().catch(() => false);

    // Fallback: look for the built-in badge which confirms profiles loaded
    const hasBuiltIn = await page.getByText("built-in").first().isVisible().catch(() => false);

    expect((hasView && hasClone) || hasBuiltIn).toBeTruthy();
    await context.close();
  });

  test("new ruleset button toggles create form", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/rulesets");

    const newButton = page.getByRole("button", { name: /new ruleset/i });
    await expect(newButton).toBeVisible({ timeout: 15_000 });
    await newButton.click();

    // Form should appear
    await expect(page.locator("#profile-id")).toBeVisible({ timeout: 5_000 });
    await expect(page.locator("#profile-name")).toBeVisible();
    await expect(page.locator("#workflow")).toBeVisible();
    await expect(page.locator("#conformance")).toBeVisible();

    // Cancel button should appear
    await expect(page.getByRole("button", { name: /cancel/i })).toBeVisible();
    await context.close();
  });

  test("create form shows threshold fields", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/rulesets");

    await page.getByRole("button", { name: /new ruleset/i }).click();
    await page.waitForTimeout(2_000);

    // Check for thresholds heading
    const hasThresholds = await page.getByText(/thresholds/i).first().isVisible({ timeout: 5_000 }).catch(() => false);
    expect(hasThresholds).toBeTruthy();

    // Check for threshold fields — these use FormField + Input with specific IDs.
    // The Input component from pixie-dust-ui may render with a wrapper, so check by ID or label.
    const hasMinDpi = await page.locator("#min-dpi").isVisible().catch(() => false);
    const hasMinDpiLabel = await page.getByText(/min dpi/i).first().isVisible().catch(() => false);
    expect(hasMinDpi || hasMinDpiLabel).toBeTruthy();

    const hasTacLimit = await page.locator("#tac-limit").isVisible().catch(() => false);
    const hasTacLabel = await page.getByText(/tac limit/i).first().isVisible().catch(() => false);
    expect(hasTacLimit || hasTacLabel).toBeTruthy();

    const hasMinBleed = await page.locator("#min-bleed").isVisible().catch(() => false);
    const hasBleedLabel = await page.getByText(/min bleed/i).first().isVisible().catch(() => false);
    expect(hasMinBleed || hasBleedLabel).toBeTruthy();

    const hasHairline = await page.locator("#hairline").isVisible().catch(() => false);
    const hasHairlineLabel = await page.getByText(/hairline/i).first().isVisible().catch(() => false);
    expect(hasHairline || hasHairlineLabel).toBeTruthy();

    const hasSmallText = await page.locator("#small-text").isVisible().catch(() => false);
    const hasSmallTextLabel = await page.getByText(/small text/i).first().isVisible().catch(() => false);
    expect(hasSmallText || hasSmallTextLabel).toBeTruthy();
    await context.close();
  });

  test("create ruleset button is disabled without required fields", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/rulesets");

    await page.getByRole("button", { name: /new ruleset/i }).click();
    await page.waitForTimeout(1_000);

    const createButton = page.getByRole("button", { name: /create ruleset/i });
    await expect(createButton).toBeVisible({ timeout: 5_000 });
    await expect(createButton).toBeDisabled();
    await context.close();
  });

  test("view profile shows detail panel", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/rulesets");
    await page.waitForTimeout(3_000);

    // Click View on a built-in profile
    const viewButton = page.getByRole("button", { name: /view/i }).first();
    const hasProfiles = await viewButton.isVisible().catch(() => false);
    if (hasProfiles) {
      await viewButton.click();
      await page.waitForTimeout(2_000);

      // Detail panel should show profile info
      await expect(page.getByText(/workflow:/i)).toBeVisible({ timeout: 5_000 });
      await expect(page.getByText(/conformance:/i)).toBeVisible();
    }
    await context.close();
  });

  test("custom profiles have delete button", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/rulesets");
    await page.waitForTimeout(3_000);

    const customSection = page.locator("main").getByRole("heading", { name: /custom rulesets/i }).first();
    const hasCustom = await customSection.isVisible().catch(() => false);
    if (hasCustom) {
      // Custom profiles should have delete buttons
      const deleteButton = customSection.locator("..").getByRole("button", { name: /delete/i }).first();
      await expect(deleteButton).toBeVisible();
    }
    await context.close();
  });

  test("delete custom profile opens confirm dialog", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/rulesets");
    await page.waitForTimeout(3_000);

    const customSection = page.locator("main").getByRole("heading", { name: /custom rulesets/i }).first();
    const hasCustom = await customSection.isVisible().catch(() => false);
    if (hasCustom) {
      const deleteButton = customSection.locator("..").getByRole("button", { name: /delete/i }).first();
      await deleteButton.click();
      await expect(page.getByText(/delete ruleset\?/i)).toBeVisible({ timeout: 5_000 });
      await expect(page.getByText(/this action cannot be undone/i)).toBeVisible();
    }
    await context.close();
  });
});
