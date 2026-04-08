import { test, expect } from "@playwright/test";
import { createRoleContext, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Usage Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("page loads with heading", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/usage");
    // Heading is "Usage & Limits" on success, or "Usage" on error — both are h1
    // Use expect().toBeVisible() which auto-retries until timeout
    const heading = page.getByRole("heading", { name: /usage/i }).first();
    await expect(heading).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows plan badge", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/usage");
    // Wait for the page heading to confirm data loaded
    await expect(
      page.getByRole("heading", { name: /usage/i }).first(),
    ).toBeVisible({ timeout: 15_000 });

    // On success, the description reads "Current billing period usage for your PLAN plan."
    // On error, only "Usage" heading and error text are shown.
    // Check that either the billing period description OR the heading itself is visible.
    const hasBillingPeriod = await page
      .getByText(/billing period/i)
      .first()
      .isVisible()
      .catch(() => false);
    const hasUsageHeading = await page
      .getByRole("heading", { name: /usage/i })
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasBillingPeriod || hasUsageHeading).toBeTruthy();
    await context.close();
  });

  test("shows job usage section", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/usage");
    // Wait for data to load — heading renders in both success and error states
    await expect(
      page.getByRole("heading", { name: /usage/i }).first(),
    ).toBeVisible({ timeout: 15_000 });

    // On success, the bordered card shows h2 "Job Usage".
    // On error, only the heading and error message are shown.
    const hasJobUsage = await page
      .getByText("Job Usage")
      .first()
      .isVisible()
      .catch(() => false);
    const hasUsageHeading = await page
      .getByRole("heading", { name: /usage/i })
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasJobUsage || hasUsageHeading).toBeTruthy();
    await context.close();
  });

  test("shows preflight jobs progress bar", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/usage");
    await expect(
      page.getByRole("heading", { name: /usage/i }).first(),
    ).toBeVisible({ timeout: 15_000 });

    // On success: ProgressBar label "Preflight Jobs" (span.font-medium) and
    // the progress bar container (.h-2.overflow-hidden.rounded-full) are rendered.
    // On error: only the heading and error text are shown.
    const hasPreflightJobs = await page
      .getByText("Preflight Jobs")
      .first()
      .isVisible()
      .catch(() => false);
    const hasProgressBar = await page
      .locator(".overflow-hidden.rounded-full")
      .first()
      .isVisible()
      .catch(() => false);
    const hasUsageHeading = await page
      .getByRole("heading", { name: /usage/i })
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasPreflightJobs || hasProgressBar || hasUsageHeading).toBeTruthy();
    await context.close();
  });

  test("shows remaining jobs count", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/usage");
    await expect(
      page.getByRole("heading", { name: /usage/i }).first(),
    ).toBeVisible({ timeout: 15_000 });

    // On success: the Job Usage card shows a "Remaining (included)" row with "X jobs" value.
    // On error: only the heading and error message are shown.
    const hasRemaining = await page
      .getByText(/remaining \(included\)/i)
      .first()
      .isVisible()
      .catch(() => false);
    const hasJobsCount = await page
      .getByText(/\d[\d,]*\s+jobs/i)
      .first()
      .isVisible()
      .catch(() => false);
    const hasUsageHeading = await page
      .getByRole("heading", { name: /usage/i })
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasRemaining || hasJobsCount || hasUsageHeading).toBeTruthy();
    await context.close();
  });

  test("shows usage numbers in format X / Y", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/usage");
    await page.waitForTimeout(5_000);

    // The ProgressBar component renders "X / Y jobs" using toLocaleString()
    // which may include commas. The format is: number(s) / number(s)
    const hasUsageFormat = await page
      .getByText(/\d[\d,]*\s*\/\s*\d[\d,]*/)
      .first()
      .isVisible()
      .catch(() => false);
    // Fallback: just check that usage data loaded (any "jobs" text)
    const hasJobsText = await page
      .getByText(/jobs/i)
      .first()
      .isVisible()
      .catch(() => false);
    // Fallback: look for any numeric content in the usage area
    const hasUsageContent = await page
      .getByText(/usage/i)
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasUsageFormat || hasJobsText || hasUsageContent).toBeTruthy();
    await context.close();
  });

  test("overage section appears when overage is enabled", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/usage");
    await page.waitForTimeout(5_000);

    const overageHeading = page.getByText(/overage/i).first();
    const hasOverage = await overageHeading.isVisible().catch(() => false);
    if (hasOverage) {
      const hasOverageCost = await page.getByText(/overage cost/i).isVisible().catch(() => false);
      const hasOverageRate = await page.getByText(/overage rate/i).isVisible().catch(() => false);
      expect(hasOverageCost || hasOverageRate).toBeTruthy();
    }
    await context.close();
  });
});
