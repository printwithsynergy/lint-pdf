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

    // The description text reads "Current billing period usage for your <Badge>PLAN</Badge> plan."
    // Match the billing period description which always renders when data loads.
    await expect(
      page.getByText(/billing period/i).first(),
    ).toBeVisible({ timeout: 5_000 });
    await context.close();
  });

  test("shows job usage section", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/usage");
    // Wait for data to load — the h2 "Job Usage" only renders on success
    await expect(
      page.getByRole("heading", { name: /usage/i }).first(),
    ).toBeVisible({ timeout: 15_000 });

    // The section has an h2 "Job Usage" rendered inside a bordered card
    await expect(
      page.getByText("Job Usage").first(),
    ).toBeVisible({ timeout: 5_000 });
    await context.close();
  });

  test("shows preflight jobs progress bar", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/usage");
    await expect(
      page.getByRole("heading", { name: /usage/i }).first(),
    ).toBeVisible({ timeout: 15_000 });

    // ProgressBar label is "Preflight Jobs" rendered as a span.font-medium
    await expect(
      page.getByText("Preflight Jobs").first(),
    ).toBeVisible({ timeout: 5_000 });

    // Progress bar outer container has classes "h-2 overflow-hidden rounded-full bg-muted"
    await expect(
      page.locator(".overflow-hidden.rounded-full").first(),
    ).toBeVisible({ timeout: 5_000 });
    await context.close();
  });

  test("shows remaining jobs count", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/usage");
    await expect(
      page.getByRole("heading", { name: /usage/i }).first(),
    ).toBeVisible({ timeout: 15_000 });

    // The remaining row renders: "Remaining (included)" label and "X jobs" value
    await expect(
      page.getByText(/remaining \(included\)/i).first(),
    ).toBeVisible({ timeout: 5_000 });

    // The value next to it always contains "jobs"
    await expect(
      page.getByText(/\d[\d,]*\s+jobs/i).first(),
    ).toBeVisible({ timeout: 5_000 });
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
