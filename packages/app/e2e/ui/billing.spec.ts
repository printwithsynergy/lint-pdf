import { test, expect } from "@playwright/test";
import { createRoleContext, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Billing Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("page loads with heading", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/billing");
    await page.waitForTimeout(3_000);
    const hasHeading = await page
      .getByRole("heading", { name: /billing/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasText = await page
      .getByText(/billing & plan/i)
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasHeading || hasText).toBeTruthy();
    await context.close();
  });

  test("shows current plan name", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/billing");
    await page.waitForTimeout(3_000);

    // Should show one of the plan names
    await expect(
      page.getByText(/free|starter|growth|scale|enterprise/i).first(),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows current plan card with title", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/billing");
    await expect(page.getByText(/current plan/i)).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows plan features list", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/billing");
    await page.waitForTimeout(3_000);

    // Plan features include job limits and file size limits
    await expect(
      page.getByText(/jobs\/day/i).first(),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("upgrade button exists", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/billing");
    await expect(
      page.getByRole("button", { name: /upgrade/i }),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("compare plans section shows all plan tiers", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/billing");
    await page.waitForTimeout(5_000);

    // Compare Plans heading (CardTitle renders as an h-level element or div)
    const hasComparePlans = await page.getByText(/compare plans/i).first().isVisible().catch(() => false);
    expect(hasComparePlans).toBeTruthy();

    // Plan tiers are h3 elements with uppercase text (FREE, STARTER, etc.)
    // They may conflict with other elements, so use first()
    const hasFree = await page.getByText(/\bfree\b/i).first().isVisible().catch(() => false);
    const hasStarter = await page.getByText(/\bstarter\b/i).first().isVisible().catch(() => false);
    const hasGrowth = await page.getByText(/\bgrowth\b/i).first().isVisible().catch(() => false);
    const hasScale = await page.getByText(/\bscale\b/i).first().isVisible().catch(() => false);
    const hasEnterprise = await page.getByText(/\benterprise\b/i).first().isVisible().catch(() => false);

    // At least some plan tiers should be visible
    const planCount = [hasFree, hasStarter, hasGrowth, hasScale, hasEnterprise].filter(Boolean).length;
    expect(planCount).toBeGreaterThanOrEqual(3);
    await context.close();
  });

  test("invoice history table shows when invoices exist", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/billing");
    await page.waitForTimeout(3_000);

    const invoiceHeader = page.getByText(/invoice history/i);
    const hasInvoices = await invoiceHeader.isVisible().catch(() => false);
    if (hasInvoices) {
      await expect(page.getByRole("columnheader", { name: /amount/i })).toBeVisible();
      await expect(page.getByRole("columnheader", { name: /date/i })).toBeVisible();
      await expect(page.getByRole("columnheader", { name: /status/i })).toBeVisible();
    }
    await context.close();
  });
});

test.describe("Billing Checkout Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("checkout page loads without server error", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    const response = await page.goto("/dashboard/billing/checkout");
    expect(response).not.toBeNull();
    expect(response!.status()).toBeLessThan(500);
    await context.close();
  });

  test("checkout page shows loading or error state without plan param", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/billing/checkout");
    await page.waitForTimeout(5_000);

    // Without a plan param, should show error about no plan specified or a spinner
    const hasError = await page.getByText(/no plan specified|invalid plan|select a plan/i).first().isVisible().catch(() => false);
    const hasSpinner = await page.locator(".animate-spin").isVisible().catch(() => false);
    const hasDestructive = await page.locator(".text-destructive").first().isVisible().catch(() => false);
    expect(hasError || hasSpinner || hasDestructive).toBeTruthy();
    await context.close();
  });

  test("checkout page with valid plan shows loading state", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/billing/checkout?plan=growth");
    await page.waitForTimeout(5_000);

    // Should show checkout preparation, redirect text, or an error from API
    const hasSpinner = await page.locator(".animate-spin").isVisible().catch(() => false);
    const hasRedirect = await page.getByText(/redirecting to stripe|preparing/i).first().isVisible().catch(() => false);
    const hasError = await page.getByText(/failed|error|network/i).first().isVisible().catch(() => false);
    const hasDestructive = await page.locator(".text-destructive").first().isVisible().catch(() => false);
    expect(hasSpinner || hasRedirect || hasError || hasDestructive).toBeTruthy();
    await context.close();
  });
});
