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
    await expect(
      page.getByRole("heading", { name: /usage & limits/i }),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows plan badge", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/usage");
    await page.waitForTimeout(3_000);

    // Should show the plan name in a badge
    await expect(
      page.getByText(/free|starter|growth|scale|enterprise/i).first(),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows job usage section", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/usage");
    await page.waitForTimeout(3_000);

    await expect(
      page.getByRole("heading", { name: /job usage/i }),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows preflight jobs progress bar", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/usage");
    await page.waitForTimeout(3_000);

    await expect(page.getByText(/preflight jobs/i)).toBeVisible({ timeout: 15_000 });
    // Progress bar should be rendered
    const progressBar = page.locator(".rounded-full.bg-muted");
    await expect(progressBar.first()).toBeVisible();
    await context.close();
  });

  test("shows remaining jobs count", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/usage");
    await page.waitForTimeout(3_000);

    await expect(
      page.getByText(/remaining \(included\)/i),
    ).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/jobs/).first()).toBeVisible();
    await context.close();
  });

  test("shows usage numbers in format X / Y", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/usage");
    await page.waitForTimeout(3_000);

    // Should show usage in "X / Y jobs" format
    await expect(
      page.getByText(/\d[\d,]* \/ \d[\d,]*/),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("overage section appears when overage is enabled", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/usage");
    await page.waitForTimeout(3_000);

    const overageHeading = page.getByRole("heading", { name: /overage/i });
    const hasOverage = await overageHeading.isVisible().catch(() => false);
    if (hasOverage) {
      await expect(page.getByText(/overage cost/i)).toBeVisible();
      await expect(page.getByText(/overage rate/i)).toBeVisible();
    }
    await context.close();
  });
});
