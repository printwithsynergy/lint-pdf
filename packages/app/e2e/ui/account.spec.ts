import { test, expect } from "@playwright/test";
import { createRoleContext, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Account Settings Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("page loads with heading", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account");
    await expect(
      page.getByRole("heading", { name: /account settings/i }),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows plan overview card", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account");
    await page.waitForTimeout(3_000);

    await expect(page.getByText(/current plan:/i)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/status:/i)).toBeVisible();
    await expect(page.getByText(/daily limit:/i)).toBeVisible();
    await context.close();
  });

  test("shows organization settings form", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account");
    await page.waitForTimeout(3_000);

    await expect(page.getByText(/organization/i).first()).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("#org-name")).toBeVisible();
    await expect(page.locator("#contact-email")).toBeVisible();
    await context.close();
  });

  test("save settings button exists", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account");
    await expect(
      page.getByRole("button", { name: /save settings/i }),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows branding section with form fields", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account");
    await page.waitForTimeout(3_000);

    await expect(
      page.getByRole("heading", { name: /branding/i }).first(),
    ).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("#brand-name")).toBeVisible();
    await expect(page.locator("#logo-url")).toBeVisible();
    await context.close();
  });

  test("shows color picker inputs for branding", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account");
    await page.waitForTimeout(3_000);

    await expect(page.getByText(/primary color/i).first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/accent color/i).first()).toBeVisible();
    await context.close();
  });

  test("save branding button exists", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account");
    await expect(
      page.getByRole("button", { name: /save branding/i }),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });
});

test.describe("Account Settings Redirect", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("settings page redirects to account page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/settings");
    await page.waitForURL(/\/dashboard\/account$/, { timeout: 15_000 });
    await context.close();
  });
});

test.describe("AI Configuration Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("page loads with heading", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/ai");
    await expect(
      page.getByRole("heading", { name: /ai configuration/i }),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows AI categories checkboxes", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/ai");
    await page.waitForTimeout(3_000);

    await expect(
      page.getByRole("heading", { name: /ai categories/i }),
    ).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/barcode detection/i)).toBeVisible();
    await expect(page.getByText(/regulatory label compliance/i)).toBeVisible();
    await expect(page.getByText(/brand compliance/i)).toBeVisible();
    await expect(page.getByText(/spell check/i)).toBeVisible();
    await expect(page.getByText(/content quality/i)).toBeVisible();
    await expect(page.getByText(/color analysis/i)).toBeVisible();
    await context.close();
  });

  test("shows AI credits section", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/ai");
    await page.waitForTimeout(3_000);

    await expect(
      page.getByRole("heading", { name: /ai credits/i }),
    ).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/used:/i)).toBeVisible();
    await expect(page.getByText(/limit:/i)).toBeVisible();
    await context.close();
  });

  test("shows custom dictionary section", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/ai");
    await page.waitForTimeout(3_000);

    await expect(
      page.getByRole("heading", { name: /custom dictionary/i }),
    ).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("textarea")).toBeVisible();
    await context.close();
  });

  test("save AI configuration button exists", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/ai");
    await expect(
      page.getByRole("button", { name: /save ai configuration/i }),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });
});

test.describe("Branding Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("page loads with heading", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/branding");
    await expect(
      page.getByRole("heading", { name: /brand profiles/i }),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows description text", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/branding");
    await expect(
      page.getByText(/control how reports appear to your customers/i),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("new profile button exists and toggles form", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/branding");

    const newButton = page.getByRole("button", { name: /new profile/i });
    await expect(newButton).toBeVisible({ timeout: 15_000 });
    await newButton.click();

    await expect(
      page.getByRole("heading", { name: /new brand profile/i }),
    ).toBeVisible({ timeout: 5_000 });
    await expect(page.locator("#profile-name")).toBeVisible();
    await expect(page.locator("#profile-type")).toBeVisible();
    await context.close();
  });

  test("create form shows profile type selector with options", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/branding");

    await page.getByRole("button", { name: /new profile/i }).click();
    await page.waitForTimeout(1_000);

    const typeSelect = page.locator("#profile-type");
    await expect(typeSelect).toBeVisible({ timeout: 5_000 });
    await expect(typeSelect.locator("option", { hasText: /custom branding/i })).toBeAttached();
    await expect(typeSelect.locator("option", { hasText: /lintpdf default/i })).toBeAttached();
    await expect(typeSelect.locator("option", { hasText: /blind/i })).toBeAttached();
    await context.close();
  });

  test("custom type shows brand name, logo, color, and footer fields", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/branding");

    await page.getByRole("button", { name: /new profile/i }).click();
    await page.waitForTimeout(1_000);

    // Custom type is default, so fields should be visible
    await expect(page.locator("#brand-name")).toBeVisible({ timeout: 5_000 });
    await expect(page.locator("#logo-url")).toBeVisible();
    await expect(page.getByText(/primary color/i)).toBeVisible();
    await expect(page.getByText(/accent color/i)).toBeVisible();
    await expect(page.locator("#footer-text")).toBeVisible();
    await expect(page.getByText(/hide footer completely/i)).toBeVisible();
    await context.close();
  });

  test("create profile button disabled without name", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/branding");

    await page.getByRole("button", { name: /new profile/i }).click();
    await page.waitForTimeout(1_000);

    const createButton = page.getByRole("button", { name: /create profile/i });
    await expect(createButton).toBeVisible({ timeout: 5_000 });
    await expect(createButton).toBeDisabled();
    await context.close();
  });

  test("existing profiles show type badge and action buttons", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/branding");
    await page.waitForTimeout(3_000);

    const editButton = page.getByRole("button", { name: /edit/i }).first();
    const hasProfiles = await editButton.isVisible().catch(() => false);
    if (hasProfiles) {
      // Should show type badge
      await expect(
        page.getByText(/custom branding|lintpdf default|blind/i).first(),
      ).toBeVisible();
      await expect(editButton).toBeVisible();
      await expect(page.getByRole("button", { name: /delete/i }).first()).toBeVisible();
    } else {
      // Empty state
      await expect(page.getByText(/no brand profiles yet/i)).toBeVisible();
    }
    await context.close();
  });

  test("delete brand profile opens confirm dialog", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/branding");
    await page.waitForTimeout(3_000);

    const deleteButton = page.getByRole("button", { name: /delete/i }).first();
    const hasProfiles = await deleteButton.isVisible().catch(() => false);
    if (hasProfiles) {
      await deleteButton.click();
      await expect(page.getByText(/delete brand profile\?/i)).toBeVisible({ timeout: 5_000 });
      await expect(page.getByText(/this action cannot be undone/i)).toBeVisible();
    }
    await context.close();
  });
});

test.describe("Color Management Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("page loads with heading", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/color");
    await expect(
      page.getByRole("heading", { name: /color management/i }),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows output condition selector", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/color");
    await page.waitForTimeout(3_000);

    await expect(
      page.getByRole("heading", { name: /output condition/i }),
    ).toBeVisible({ timeout: 15_000 });
    // Should have a select dropdown with "None" option
    await expect(page.getByText(/none \(no gamut checking\)/i)).toBeAttached();
    await context.close();
  });

  test("shows default thresholds section", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/color");
    await page.waitForTimeout(3_000);

    await expect(
      page.getByRole("heading", { name: /default thresholds/i }),
    ).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/tac limit/i)).toBeVisible();
    await expect(page.getByText(/safety zone margin/i)).toBeVisible();
    await expect(page.getByText(/target market/i)).toBeVisible();
    await expect(page.getByText(/hp indigo epm mode/i)).toBeVisible();
    await context.close();
  });

  test("shows Pantone overrides section", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/color");
    await page.waitForTimeout(3_000);

    await expect(
      page.getByRole("heading", { name: /pantone color overrides/i }),
    ).toBeVisible({ timeout: 15_000 });
    // Should have Add Override and Import CSV buttons
    await expect(page.getByRole("button", { name: /add override/i })).toBeVisible();
    await expect(page.getByText(/import csv/i)).toBeVisible();
    await context.close();
  });

  test("add override form shows name and lab value fields", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/color");
    await page.waitForTimeout(3_000);

    await page.getByRole("button", { name: /add override/i }).click();
    await page.waitForTimeout(1_000);

    await expect(page.getByPlaceholder(/pantone 485/i)).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText(/lab values/i)).toBeVisible();
    await expect(page.getByText(/cmyk bridge/i)).toBeVisible();
    await context.close();
  });

  test("save color configuration button exists", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/color");
    await expect(
      page.getByRole("button", { name: /save color configuration/i }),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });
});
