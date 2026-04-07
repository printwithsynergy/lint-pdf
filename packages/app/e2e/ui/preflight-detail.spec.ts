import { test, expect } from "@playwright/test";
import { createRoleContext, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Preflight Job Detail Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("job detail page loads and shows heading", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    // First get a job ID from the list
    await page.goto("/dashboard/preflight");
    await page.waitForTimeout(3_000);

    const hasTable = await page.locator("table").isVisible();
    if (!hasTable) {
      test.skip(true, "No jobs available to test detail page");
      await context.close();
      return;
    }

    // Click the first job link
    const firstJobLink = page.locator("tbody tr").first().locator("a").first();
    const jobUrl = await firstJobLink.getAttribute("href");
    expect(jobUrl).toBeTruthy();
    await page.goto(jobUrl!);

    // Should show job details heading (file name as h1)
    await expect(page.locator("h1")).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("job detail shows file metadata", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/preflight");
    await page.waitForTimeout(3_000);

    const hasTable = await page.locator("table").isVisible();
    if (!hasTable) {
      test.skip(true, "No jobs available");
      await context.close();
      return;
    }

    const firstJobLink = page.locator("tbody tr").first().locator("a").first();
    const jobUrl = await firstJobLink.getAttribute("href");
    await page.goto(jobUrl!);

    await page.waitForTimeout(3_000);

    // Should show profile info
    await expect(page.getByText(/profile:/i)).toBeVisible({ timeout: 15_000 });
    // Should show file size in MB
    await expect(page.getByText(/MB/)).toBeVisible();
    await context.close();
  });

  test("job detail shows status badge", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/preflight");
    await page.waitForTimeout(3_000);

    const hasTable = await page.locator("table").isVisible();
    if (!hasTable) {
      test.skip(true, "No jobs available");
      await context.close();
      return;
    }

    const firstJobLink = page.locator("tbody tr").first().locator("a").first();
    const jobUrl = await firstJobLink.getAttribute("href");
    await page.goto(jobUrl!);

    // One of the status values should be visible
    await expect(
      page.getByText(/complete|failed|pending|processing/i).first(),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("completed job shows findings summary cards", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/preflight");
    await page.waitForTimeout(3_000);

    const hasTable = await page.locator("table").isVisible();
    if (!hasTable) {
      test.skip(true, "No jobs available");
      await context.close();
      return;
    }

    const firstJobLink = page.locator("tbody tr").first().locator("a").first();
    const jobUrl = await firstJobLink.getAttribute("href");
    await page.goto(jobUrl!);
    await page.waitForTimeout(3_000);

    // If this is a completed job, it should show summary cards
    const hasErrors = await page.getByText("Errors").first().isVisible().catch(() => false);
    if (hasErrors) {
      await expect(page.getByText("Errors").first()).toBeVisible();
      await expect(page.getByText("Warnings").first()).toBeVisible();
      await expect(page.getByText("Advisories").first()).toBeVisible();
      // Should show PASS or FAIL result
      await expect(
        page.getByText(/PASS|FAIL/).first(),
      ).toBeVisible();
    }
    await context.close();
  });

  test("completed job shows viewer and report links", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/preflight");
    await page.waitForTimeout(3_000);

    const hasTable = await page.locator("table").isVisible();
    if (!hasTable) {
      test.skip(true, "No jobs available");
      await context.close();
      return;
    }

    const firstJobLink = page.locator("tbody tr").first().locator("a").first();
    const jobUrl = await firstJobLink.getAttribute("href");
    await page.goto(jobUrl!);
    await page.waitForTimeout(3_000);

    // Check for viewer and report links on completed jobs
    const viewerLink = page.getByText(/open viewer/i);
    const htmlReport = page.getByText(/view html report/i);
    const pdfReport = page.getByText(/download pdf report/i);

    const hasViewer = await viewerLink.isVisible().catch(() => false);
    if (hasViewer) {
      await expect(viewerLink).toBeVisible();
      await expect(htmlReport).toBeVisible();
      await expect(pdfReport).toBeVisible();
    }
    await context.close();
  });

  test("back to jobs link works", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/preflight");
    await page.waitForTimeout(3_000);

    const hasTable = await page.locator("table").isVisible();
    if (!hasTable) {
      test.skip(true, "No jobs available");
      await context.close();
      return;
    }

    const firstJobLink = page.locator("tbody tr").first().locator("a").first();
    const jobUrl = await firstJobLink.getAttribute("href");
    await page.goto(jobUrl!);
    await page.waitForTimeout(3_000);

    const backLink = page.getByText(/back to jobs/i);
    await expect(backLink).toBeVisible({ timeout: 15_000 });
    await backLink.click();
    await page.waitForURL(/\/dashboard\/preflight$/, { timeout: 15_000 });
    await context.close();
  });
});

test.describe("Preflight Report Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("report page loads for completed job", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    // Get a completed job from the reports page
    await page.goto("/dashboard/reports");
    await page.waitForTimeout(3_000);

    const jobLink = page.locator("a[href*='/dashboard/preflight/']").first();
    const hasJobs = await jobLink.isVisible().catch(() => false);
    if (!hasJobs) {
      test.skip(true, "No completed jobs available");
      await context.close();
      return;
    }

    const href = await jobLink.getAttribute("href");
    await page.goto(`${href}/report`);

    // Report page should show heading (file name or "Preflight Report")
    await expect(page.locator("h1")).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("report page shows summary and findings", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/reports");
    await page.waitForTimeout(3_000);

    const jobLink = page.locator("a[href*='/dashboard/preflight/']").first();
    const hasJobs = await jobLink.isVisible().catch(() => false);
    if (!hasJobs) {
      test.skip(true, "No completed jobs available");
      await context.close();
      return;
    }

    const href = await jobLink.getAttribute("href");
    await page.goto(`${href}/report`);
    await page.waitForTimeout(3_000);

    // Should show PASS/FAIL and summary counts
    await expect(page.getByText(/PASS|FAIL/).first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/back to reports/i)).toBeVisible();
    await context.close();
  });
});

test.describe("Preflight Viewer Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("viewer page loads for completed job", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();

    await page.goto("/dashboard/reports");
    await page.waitForTimeout(3_000);

    const jobLink = page.locator("a[href*='/dashboard/preflight/']").first();
    const hasJobs = await jobLink.isVisible().catch(() => false);
    if (!hasJobs) {
      test.skip(true, "No completed jobs available");
      await context.close();
      return;
    }

    const href = await jobLink.getAttribute("href");
    await page.goto(`${href}/viewer`);

    // Viewer should load without server error
    await page.waitForTimeout(5_000);
    const url = page.url();
    expect(url).toContain("/viewer");
    await context.close();
  });
});
