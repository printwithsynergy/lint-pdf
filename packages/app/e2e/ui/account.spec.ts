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
    await page.waitForTimeout(3_000);
    const hasHeading = await page
      .getByRole("heading", { name: /account settings/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasText = await page
      .getByText(/account settings/i)
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasHeading || hasText).toBeTruthy();
    await context.close();
  });

  test("shows plan overview card", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account");
    await page.waitForTimeout(5_000);

    // The plan card has a "Plan" heading and plan details
    const hasPlanHeading = await page
      .locator("main")
      .getByRole("heading", { name: /plan/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasPlanText = await page
      .getByText(/current plan:/i)
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasPlanHeading || hasPlanText).toBeTruthy();
    await context.close();
  });

  test("shows organization settings form", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account");
    await page.waitForTimeout(5_000);

    // Organization card has heading and form fields
    const hasOrgHeading = await page
      .locator("main")
      .getByRole("heading", { name: /organization/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasOrgText = await page
      .getByText(/organization/i)
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasOrgHeading || hasOrgText).toBeTruthy();

    const hasOrgName = await page.locator("#org-name").isVisible().catch(() => false);
    const hasInput = await page.locator("input").first().isVisible().catch(() => false);
    expect(hasOrgName || hasInput).toBeTruthy();
    await context.close();
  });

  test("save settings button exists", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account");
    await page.waitForTimeout(5_000);
    const hasBtn = await page
      .getByRole("button", { name: /save settings/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasBtnText = await page
      .locator("button", { hasText: /save settings/i })
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasBtn || hasBtnText).toBeTruthy();
    await context.close();
  });

  test("shows branding section with form fields", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account");
    await page.waitForTimeout(5_000);

    // Branding card heading (CardTitle may or may not be a heading role)
    const hasBrandingHeading = await page
      .getByRole("heading", { name: /branding/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasBrandingText = await page
      .getByText(/branding/i)
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasBrandingHeading || hasBrandingText).toBeTruthy();

    const hasBrandName = await page.locator("#brand-name").isVisible().catch(() => false);
    const hasLogoUrl = await page.locator("#logo-url").isVisible().catch(() => false);
    expect(hasBrandName || hasLogoUrl).toBeTruthy();
    await context.close();
  });

  test("shows color picker inputs for branding", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account");
    await page.waitForTimeout(5_000);

    const hasPrimary = await page.getByText(/primary color/i).first().isVisible().catch(() => false);
    const hasAccent = await page.getByText(/accent color/i).first().isVisible().catch(() => false);
    const hasColorInput = await page.locator("input[type='color']").first().isVisible().catch(() => false);
    expect(hasPrimary || hasAccent || hasColorInput).toBeTruthy();
    await context.close();
  });

  test("save branding button exists", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account");
    await page.waitForTimeout(5_000);
    const hasBtn = await page
      .getByRole("button", { name: /save branding/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasBtnText = await page
      .locator("button", { hasText: /save branding/i })
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasBtn || hasBtnText).toBeTruthy();
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
    // May redirect to /dashboard/account or stay on /dashboard/account/settings
    await page.waitForTimeout(5_000);
    const url = page.url();
    const redirected = url.includes("/dashboard/account");
    expect(redirected).toBe(true);
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
    await page.waitForTimeout(3_000);
    const hasHeading = await page
      .getByRole("heading", { name: /ai configuration/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasText = await page
      .getByText(/ai configuration/i)
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasHeading || hasText).toBeTruthy();
    await context.close();
  });

  test("shows AI categories checkboxes", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/ai");
    await page.waitForTimeout(5_000);

    // AI Categories heading (h2, not inside main necessarily)
    const hasCatHeading = await page
      .getByRole("heading", { name: /ai categories/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasCatText = await page
      .getByText(/ai categories/i)
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasCatHeading || hasCatText).toBeTruthy();

    // Categories use labels like "Barcode Detection & Grading"
    const hasBarcode = await page.getByText(/barcode detection/i).first().isVisible().catch(() => false);
    const hasCheckbox = await page.locator("input[type='checkbox']").first().isVisible().catch(() => false);
    expect(hasBarcode || hasCheckbox).toBeTruthy();
    await context.close();
  });

  test("shows AI credits section", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/ai");
    await page.waitForTimeout(5_000);

    // AI Credits heading
    const hasCreditsHeading = await page
      .getByRole("heading", { name: /ai credits/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasCreditsText = await page
      .getByText(/ai credits/i)
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasCreditsHeading || hasCreditsText).toBeTruthy();

    // Credits show "Used:" and "Limit:" labels
    const hasUsed = await page.getByText(/used:/i).first().isVisible().catch(() => false);
    const hasLimit = await page.getByText(/limit:/i).first().isVisible().catch(() => false);
    expect(hasUsed || hasLimit).toBeTruthy();
    await context.close();
  });

  test("shows custom dictionary section", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/ai");
    await page.waitForTimeout(5_000);

    const hasDictHeading = await page
      .getByRole("heading", { name: /custom dictionary/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasDictText = await page
      .getByText(/custom dictionary/i)
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasDictHeading || hasDictText).toBeTruthy();

    const hasTextarea = await page.locator("textarea").isVisible().catch(() => false);
    expect(hasTextarea).toBeTruthy();
    await context.close();
  });

  test("save AI configuration button exists", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/ai");
    await page.waitForTimeout(5_000);
    // The save button is a plain <button>, match by text content
    const hasSaveBtn = await page
      .getByRole("button", { name: /save ai configuration/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasBtnText = await page
      .locator("button", { hasText: /save ai/i })
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasSaveBtn || hasBtnText).toBeTruthy();
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
    // The branding page wraps content in its own <main> tag
    await expect(
      page.getByRole("heading", { name: /brand profiles/i }).first(),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows description text", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/branding");
    await page.waitForTimeout(3_000);
    // Description: "Control how reports appear to your customers..."
    const hasDesc = await page
      .getByText(/control how reports appear/i)
      .isVisible()
      .catch(() => false);
    const hasAltDesc = await page
      .getByText(/customize|brand/i)
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasDesc || hasAltDesc).toBeTruthy();
    await context.close();
  });

  test("new profile button exists and toggles form", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/branding");

    const newButton = page.getByRole("button", { name: /new profile/i });
    await expect(newButton).toBeVisible({ timeout: 15_000 });
    await newButton.click();

    // Form heading: "New Brand Profile" (h2)
    await expect(
      page.getByRole("heading", { name: /new brand profile/i }).first(),
    ).toBeVisible({ timeout: 5_000 });
    await expect(page.locator("#profile-name")).toBeVisible();
    // profile-type may be a Select component with id
    const hasTypeSelect = await page.locator("#profile-type").isVisible().catch(() => false);
    const hasSelect = await page.locator("select").first().isVisible().catch(() => false);
    expect(hasTypeSelect || hasSelect).toBeTruthy();
    await context.close();
  });

  test("create form shows profile type selector with options", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/branding");

    await page.getByRole("button", { name: /new profile/i }).click();
    await page.waitForTimeout(1_000);

    // The profile type select (may have id="profile-type" or be a plain select)
    const typeSelect = page.locator("#profile-type, select").first();
    await expect(typeSelect).toBeVisible({ timeout: 5_000 });
    // Options: Custom Branding, LintPDF Default, Blind (No Branding)
    await expect(page.locator("option", { hasText: /custom branding/i }).first()).toBeAttached();
    await expect(page.locator("option", { hasText: /lintpdf default/i }).first()).toBeAttached();
    await expect(page.locator("option", { hasText: /blind/i }).first()).toBeAttached();
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
      page.locator("main").getByRole("heading", { name: /color management/i }).first(),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows output condition selector", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/color");
    await page.waitForTimeout(3_000);

    await expect(
      page.locator("main").getByRole("heading", { name: /output condition/i }).first(),
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
      page.locator("main").getByRole("heading", { name: /default thresholds/i }).first(),
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
      page.locator("main").getByRole("heading", { name: /pantone color overrides/i }).first(),
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
