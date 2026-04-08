import { test, expect } from "@playwright/test";
import { createRoleContext, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Preflight Jobs Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("page loads with heading", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/preflight");
    await expect(
      page.locator("main").getByRole("heading", { name: /preflight jobs/i }).first(),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows total jobs count", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/preflight");
    await expect(page.getByText(/\d+ total jobs/)).toBeVisible({
      timeout: 15_000,
    });
    await context.close();
  });

  test("file upload form exists with FileUpload component", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/preflight");
    await expect(
      page.getByText(/submit pdf for preflight/i),
    ).toBeVisible({ timeout: 15_000 });
    // FileUpload component renders a drop zone with help text
    await expect(
      page.getByText(/drag and drop a pdf or click to browse/i),
    ).toBeVisible();
    await context.close();
  });

  test("profile selector dropdown exists with default option", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/preflight");
    const profileSelect = page.locator("select#profile");
    await expect(profileSelect).toBeVisible({ timeout: 15_000 });
    // Default option should always be present
    await expect(profileSelect.locator("option", { hasText: "Default" })).toBeAttached();
    await context.close();
  });

  test("submit button exists and is disabled without file", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/preflight");
    const submitButton = page.getByRole("button", { name: /run preflight/i });
    await expect(submitButton).toBeVisible({ timeout: 15_000 });
    await expect(submitButton).toBeDisabled();
    await context.close();
  });

  test("job list table renders with correct headers when jobs exist", async ({ browser }) => {
    test.fixme(true, "Preflight page loading timing is inconsistent — needs investigation");
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/preflight");

    // Wait for the page to load — look for Run Preflight button or heading
    await expect(
      page.getByRole("button", { name: /run preflight/i }),
    ).toBeVisible({ timeout: 15_000 });

    // Wait for jobs to load — the skeleton disappears and either table or empty state shows
    // Use a combined locator to wait for any of these states
    await expect(
      page.getByText(/no preflight jobs yet/i)
        .or(page.getByRole("columnheader", { name: /file/i }))
        .or(page.getByText(/failed to load/i))
        .first(),
    ).toBeVisible({ timeout: 15_000 });

    const hasJobTable = await page
      .getByRole("columnheader", { name: /file/i })
      .isVisible()
      .catch(() => false);

    if (hasJobTable) {
      await expect(page.getByRole("columnheader", { name: /profile/i })).toBeVisible();
      await expect(page.getByRole("columnheader", { name: /status/i })).toBeVisible();
    }
    await context.close();
  });

  test("job rows show view and delete buttons when jobs exist", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/preflight");
    await page.waitForTimeout(3_000);

    const hasTable = await page.locator("table").isVisible();
    if (hasTable) {
      const firstRow = page.locator("tbody tr").first();
      await expect(firstRow.getByRole("button", { name: /view/i })).toBeVisible();
      await expect(firstRow.getByRole("button", { name: /delete/i })).toBeVisible();
    }
    await context.close();
  });

  test("delete button opens confirm dialog", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/preflight");
    await page.waitForTimeout(3_000);

    const hasTable = await page.locator("table").isVisible();
    if (hasTable) {
      const deleteButton = page.locator("tbody tr").first().getByRole("button", { name: /delete/i });
      await deleteButton.click();
      await expect(page.getByText(/delete job\?/i)).toBeVisible({ timeout: 5_000 });
      await expect(page.getByText(/this action cannot be undone/i)).toBeVisible();
      // Close the dialog
      const closeButton = page.getByRole("button", { name: /cancel/i });
      if (await closeButton.isVisible()) {
        await closeButton.click();
      }
    }
    await context.close();
  });

  test("pagination controls appear when there are multiple pages of jobs", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/preflight");
    await page.waitForTimeout(3_000);

    // Pagination only renders when totalPages > 1
    const prevButton = page.getByRole("button", { name: /previous/i });
    const nextButton = page.getByRole("button", { name: /next/i });
    const hasPagination = await prevButton.isVisible().catch(() => false);
    if (hasPagination) {
      await expect(prevButton).toBeVisible();
      await expect(nextButton).toBeVisible();
      await expect(page.getByText(/page \d+ of \d+/i)).toBeVisible();
    }
    await context.close();
  });

  test("empty state shows when no jobs exist", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/preflight");
    await page.waitForTimeout(3_000);

    const hasTable = await page.locator("table").isVisible();
    if (!hasTable) {
      await expect(page.getByText(/no preflight jobs yet/i)).toBeVisible();
      await expect(
        page.getByText(/upload a pdf above to run your first preflight/i),
      ).toBeVisible();
    }
    await context.close();
  });
});
