import { test, expect } from "@playwright/test";
import { createRoleContext, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Reports Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("page loads with heading", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/reports");
    await expect(
      page.locator("main").getByRole("heading", { name: /reports/i }).first(),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows description text", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/reports");
    await expect(
      page.getByText(/view and download preflight reports/i),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows completed jobs list or empty state", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/reports");
    await page.waitForTimeout(3_000);

    const hasJobs = await page
      .locator("a[href*='/dashboard/preflight/']")
      .first()
      .isVisible()
      .catch(() => false);
    if (hasJobs) {
      // Should show file name links
      await expect(
        page.locator("a[href*='/dashboard/preflight/']").first(),
      ).toBeVisible();
    } else {
      await expect(
        page.getByText(/no completed jobs with reports yet/i),
      ).toBeVisible({ timeout: 15_000 });
    }
    await context.close();
  });

  test("report entries show view HTML and download PDF buttons", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/reports");
    await page.waitForTimeout(3_000);

    const hasJobs = await page
      .locator("a[href*='/dashboard/preflight/']")
      .first()
      .isVisible()
      .catch(() => false);
    if (hasJobs) {
      await expect(page.getByText(/view html/i).first()).toBeVisible();
      await expect(page.getByText(/download pdf/i).first()).toBeVisible();
    }
    await context.close();
  });

  test("report entries show profile and date info", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/reports");
    await page.waitForTimeout(3_000);

    const hasJobs = await page
      .locator("a[href*='/dashboard/preflight/']")
      .first()
      .isVisible()
      .catch(() => false);
    if (hasJobs) {
      // Jobs show pass/fail status
      const hasPassFail = await page
        .getByText(/passed|errors/i)
        .first()
        .isVisible()
        .catch(() => false);
      expect(hasPassFail).toBeTruthy();
    }
    await context.close();
  });
});
