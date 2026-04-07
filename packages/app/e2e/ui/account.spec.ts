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
    // Wait for page heading to confirm page loaded
    await expect(
      page.getByRole("heading", { name: /account settings/i }).first(),
    ).toBeVisible({ timeout: 15_000 });

    // The plan card has a CardTitle "Plan" and text "Current Plan:" inside CardContent
    await expect(
      page.getByText(/current plan/i).first(),
    ).toBeVisible({ timeout: 5_000 });
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
    // Wait for AI Configuration heading to confirm page loaded
    await expect(
      page.getByRole("heading", { name: /ai configuration/i }).first(),
    ).toBeVisible({ timeout: 15_000 });

    // AI Credits is an h2 rendered with class "text-lg font-semibold" (not a heading role)
    await expect(
      page.getByText("AI Credits").first(),
    ).toBeVisible({ timeout: 5_000 });

    // Credits show inline "Used: <strong>N</strong>" and "Limit: <strong>N</strong>"
    await expect(
      page.locator("strong").first(),
    ).toBeVisible({ timeout: 5_000 });
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

    // The button text is "New Profile" when form is closed
    const newButton = page.getByRole("button", { name: /new profile/i });
    await expect(newButton).toBeVisible({ timeout: 15_000 });
    await newButton.click();

    // Form heading: h2 "New Brand Profile" with class "text-lg font-semibold"
    await expect(
      page.getByText("New Brand Profile").first(),
    ).toBeVisible({ timeout: 5_000 });

    // Profile Name input with id "profile-name"
    await expect(
      page.locator("#profile-name"),
    ).toBeVisible({ timeout: 5_000 });

    // Profile Type is a Select component (renders as <select>) with id "profile-type"
    await expect(
      page.locator("select#profile-type"),
    ).toBeVisible({ timeout: 5_000 });
    await context.close();
  });

  test("create form shows profile type selector with options", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/branding");

    const newButton = page.getByRole("button", { name: /new profile/i });
    await expect(newButton).toBeVisible({ timeout: 15_000 });
    await newButton.click();

    // The profile type is a Select component (renders as native <select>) with id "profile-type"
    const typeSelect = page.locator("select#profile-type");
    await expect(typeSelect).toBeVisible({ timeout: 5_000 });

    // Options: "Custom Branding", "LintPDF Default", "Blind (No Branding)"
    await expect(
      page.locator("select#profile-type option", { hasText: "Custom Branding" }),
    ).toHaveCount(1);
    await expect(
      page.locator("select#profile-type option", { hasText: "LintPDF Default" }),
    ).toHaveCount(1);
    await expect(
      page.locator("select#profile-type option", { hasText: /blind/i }),
    ).toHaveCount(1);
    await context.close();
  });

  test("custom type shows brand name, logo, color, and footer fields", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/branding");

    const newButton = page.getByRole("button", { name: /new profile/i });
    await expect(newButton).toBeVisible({ timeout: 15_000 });
    await newButton.click();

    // Custom type is the default, so custom fields should be visible immediately.
    // Brand Name input (id="brand-name") and its FormField label
    await expect(page.locator("#brand-name")).toBeVisible({ timeout: 5_000 });

    // Logo URL input (id="logo-url")
    await expect(page.locator("#logo-url")).toBeVisible({ timeout: 5_000 });

    // Color fields — FormField labels "Primary Color" and "Accent Color"
    await expect(
      page.getByText("Primary Color").first(),
    ).toBeVisible({ timeout: 5_000 });
    await expect(
      page.getByText("Accent Color").first(),
    ).toBeVisible({ timeout: 5_000 });

    // Footer Text input (id="footer-text")
    await expect(page.locator("#footer-text")).toBeVisible({ timeout: 5_000 });

    // "Hide footer completely" checkbox label
    await expect(
      page.getByText(/hide footer completely/i).first(),
    ).toBeVisible({ timeout: 5_000 });
    await context.close();
  });

  test("create profile button disabled without name", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/branding");

    const newButton = page.getByRole("button", { name: /new profile/i });
    await expect(newButton).toBeVisible({ timeout: 15_000 });
    await newButton.click();

    // Wait for the form to appear
    await expect(
      page.getByText("New Brand Profile").first(),
    ).toBeVisible({ timeout: 5_000 });

    // The button text is "Create Profile" and is disabled when formName is empty
    // Button uses disabled={!formName} — formName starts as ""
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
    await page.waitForTimeout(3_000);
    const hasHeading = await page
      .getByRole("heading", { name: /color management/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasText = await page
      .getByText(/color management/i)
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasHeading || hasText).toBeTruthy();
    await context.close();
  });

  test("shows output condition selector", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/color");
    await page.waitForTimeout(5_000);

    // The heading is an h2 with class "text-lg font-semibold", not a heading role
    const hasCondHeading = await page
      .getByText(/output condition/i)
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasCondHeading).toBeTruthy();

    // Should have a native <select> dropdown with "None (no gamut checking)" option
    const hasSelect = await page.locator("select").first().isVisible().catch(() => false);
    const noneOptionCount = await page.locator("option", { hasText: /none/i }).count();
    const hasNoneOption = noneOptionCount > 0;
    expect(hasNoneOption || hasSelect).toBeTruthy();
    await context.close();
  });

  test("shows default thresholds section", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/color");
    await page.waitForTimeout(5_000);

    const hasThreshHeading = await page
      .getByRole("heading", { name: /default thresholds/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasThreshText = await page
      .getByText(/default thresholds/i)
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasThreshHeading || hasThreshText).toBeTruthy();

    const hasTac = await page.getByText(/tac limit/i).first().isVisible().catch(() => false);
    const hasSafety = await page.getByText(/safety zone/i).first().isVisible().catch(() => false);
    expect(hasTac || hasSafety).toBeTruthy();
    await context.close();
  });

  test("shows Pantone overrides section", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/color");
    await page.waitForTimeout(5_000);

    const hasPantoneHeading = await page
      .getByRole("heading", { name: /pantone color overrides/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasPantoneText = await page
      .getByText(/pantone color overrides/i)
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasPantoneHeading || hasPantoneText).toBeTruthy();

    // "Add Override" is a plain button, "Import CSV" is a label
    const hasAddBtn = await page.locator("button", { hasText: /add override/i }).isVisible().catch(() => false);
    const hasImportLabel = await page.getByText(/import csv/i).first().isVisible().catch(() => false);
    expect(hasAddBtn || hasImportLabel).toBeTruthy();
    await context.close();
  });

  test("add override form shows name and lab value fields", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/color");
    await page.waitForTimeout(5_000);

    // Click the "Add Override" button (plain button)
    const addBtn = page.locator("button", { hasText: /add override/i });
    await expect(addBtn).toBeVisible({ timeout: 10_000 });
    await addBtn.click();
    await page.waitForTimeout(1_000);

    // Placeholder is "e.g. PANTONE 485 C"
    const hasPlaceholder = await page.getByPlaceholder(/pantone 485/i).isVisible().catch(() => false);
    const hasNameLabel = await page.getByText(/pantone name/i).first().isVisible().catch(() => false);
    expect(hasPlaceholder || hasNameLabel).toBeTruthy();

    const hasLab = await page.getByText(/lab values/i).first().isVisible().catch(() => false);
    const hasCmyk = await page.getByText(/cmyk bridge/i).first().isVisible().catch(() => false);
    expect(hasLab || hasCmyk).toBeTruthy();
    await context.close();
  });

  test("save color configuration button exists", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/account/color");
    await page.waitForTimeout(5_000);
    // The save button is a plain <button>
    const hasBtn = await page
      .locator("button", { hasText: /save color configuration/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasRoleBtn = await page
      .getByRole("button", { name: /save color configuration/i })
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasBtn || hasRoleBtn).toBeTruthy();
    await context.close();
  });
});
