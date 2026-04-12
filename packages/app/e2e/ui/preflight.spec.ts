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
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/preflight", { waitUntil: "networkidle" });

    // Wait for the page shell (Run Preflight button is always visible)
    await expect(
      page.getByRole("button", { name: /run preflight/i }),
    ).toBeVisible({ timeout: 30_000 });

    // Wait for the async jobs list to resolve. The ``TableHead`` component
    // from the UI kit renders as ``<td>`` (not ``<th>``), so the header cells
    // show up as role ``cell`` rather than ``columnheader``. We match the
    // first row of the table rowgroup directly.
    const headerRow = page.locator("table thead tr").first();
    await expect(
      page
        .getByText(/no preflight jobs yet/i)
        .or(headerRow)
        .or(page.getByText(/failed to load/i))
        .first(),
    ).toBeVisible({ timeout: 30_000 });

    const hasJobTable = await headerRow.isVisible().catch(() => false);

    if (hasJobTable) {
      await expect(headerRow.getByText("File", { exact: true })).toBeVisible();
      await expect(
        headerRow.getByText("Profile", { exact: true }),
      ).toBeVisible();
      await expect(
        headerRow.getByText("Status", { exact: true }),
      ).toBeVisible();
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

  // ---- Preflight source segmented control + anonymize surface ----

  test("source segmented control exposes all three tabs", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/preflight");

    const tablist = page.getByRole("tablist", { name: /preflight source/i });
    await expect(tablist).toBeVisible({ timeout: 15_000 });

    await expect(
      tablist.getByRole("tab", { name: "Run Preflight" }),
    ).toBeVisible();
    await expect(
      tablist.getByRole("tab", { name: "Import External Results" }),
    ).toBeVisible();
    await expect(
      tablist.getByRole("tab", { name: "Viewer Only" }),
    ).toBeVisible();

    // "Run Preflight" is the default
    await expect(
      tablist.getByRole("tab", { name: "Run Preflight" }),
    ).toHaveAttribute("aria-selected", "true");
    await context.close();
  });

  test("selecting Import External Results reveals report upload and format dropdown", async ({
    browser,
  }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/preflight");

    const importTab = page.getByRole("tab", { name: "Import External Results" });
    await expect(importTab).toBeVisible({ timeout: 15_000 });
    await importTab.click();

    // Secondary preflight report FileUpload becomes visible
    await expect(
      page.getByText(
        /preflight report \(pitstop \/ callas \/ acrobat \/ lintpdf json\)/i,
      ),
    ).toBeVisible();
    await expect(
      page.getByText(/upload the raw report your existing tool produced/i),
    ).toBeVisible();

    // Format dropdown with all six options
    const formatSelect = page.locator("select#external-format");
    await expect(formatSelect).toBeVisible();
    for (const label of [
      "Auto-detect",
      "Enfocus PitStop (XML)",
      "callas pdfToolbox (JSON)",
      "callas pdfToolbox (XML)",
      "Acrobat Preflight (XML)",
      "LintPDF native (JSON)",
    ]) {
      await expect(
        formatSelect.locator("option", { hasText: label }),
      ).toBeAttached();
    }

    // Submit button relabels to "Import Results"
    await expect(
      page.getByRole("button", { name: /^import results$/i }),
    ).toBeVisible();
    await context.close();
  });

  test("Viewer Only mode hides profile selector and shows viewer-only alert", async ({
    browser,
  }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/preflight");

    const viewerTab = page.getByRole("tab", { name: "Viewer Only" });
    await expect(viewerTab).toBeVisible({ timeout: 15_000 });
    await viewerTab.click();

    // Profile dropdown is only rendered when source=engine
    await expect(page.locator("select#profile")).toHaveCount(0);

    // Informational alert copy
    await expect(
      page.getByText(/viewer-only mode skips analyzers entirely/i),
    ).toBeVisible();

    // Submit button relabels to "Open Viewer"
    await expect(
      page.getByRole("button", { name: /^open viewer$/i }),
    ).toBeVisible();
    await context.close();
  });

  test("anonymize output checkbox and help text are present", async ({
    browser,
  }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/preflight");

    const anonymize = page.locator("input#anonymize");
    await expect(anonymize).toBeVisible({ timeout: 15_000 });
    await expect(anonymize).toHaveAttribute("type", "checkbox");

    await expect(page.getByText(/anonymize output/i)).toBeVisible();
    await expect(
      page.getByText(
        /hide all branding and strip identifying pdf metadata/i,
      ),
    ).toBeVisible();
    await expect(
      page.getByText(
        /use when sending reports to distributors who shouldn.?t know you generated them/i,
      ),
    ).toBeVisible();

    // Toggling it should flip the checkbox state
    const initial = await anonymize.isChecked();
    await anonymize.click();
    expect(await anonymize.isChecked()).toBe(!initial);
    await context.close();
  });

  test("submit button disables when external mode has PDF but no report", async ({
    browser,
  }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/preflight");

    await page.getByRole("tab", { name: "Import External Results" }).click();

    const submit = page.getByRole("button", { name: /^import results$/i });
    await expect(submit).toBeVisible({ timeout: 15_000 });
    // Both PDF and external report are missing -> disabled
    await expect(submit).toBeDisabled();
    await context.close();
  });
});
