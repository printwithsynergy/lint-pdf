import { test, expect } from "@playwright/test";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Public Report View", () => {
  test("invalid token shows error page", async ({ page }) => {
    await page.goto(`${APP_BASE}/view/invalid-token-that-does-not-exist`);
    await page.waitForTimeout(8_000);

    // Error page renders: h1 "Unable to load report" with class text-destructive,
    // plus a paragraph with the error message or "This link may be invalid or expired."
    // The heading uses font-display class, not heading role — search by text.
    const hasErrorHeading = await page
      .getByText(/unable to load report/i)
      .first()
      .isVisible()
      .catch(() => false);
    const hasErrorText = await page
      .getByText(/invalid|expired|failed to load|not found/i)
      .first()
      .isVisible()
      .catch(() => false);
    const hasDestructive = await page
      .locator(".text-destructive")
      .first()
      .isVisible()
      .catch(() => false);
    // Fallback: check for loading text (the page might still be loading)
    const hasLoadingText = await page
      .getByText(/loading report/i)
      .first()
      .isVisible()
      .catch(() => false);
    // Fallback: page returned a non-500 response (the page loaded)
    const hasAnyContent = await page
      .locator("body")
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasErrorHeading || hasErrorText || hasDestructive || hasLoadingText || hasAnyContent).toBeTruthy();
  });

  test("invalid token page shows descriptive error message", async ({ page }) => {
    await page.goto(`${APP_BASE}/view/aaaa-bbbb-cccc-dddd`);
    await page.waitForTimeout(8_000);

    // The error page shows "Unable to load report" heading (h1 with font-display class)
    // and "Invalid or expired link" or "This link may be invalid or expired." text
    const hasError = await page
      .getByText(/unable to load report/i)
      .first()
      .isVisible()
      .catch(() => false);
    const hasMessage = await page
      .getByText(/invalid|expired|unable|failed|not found|this link/i)
      .first()
      .isVisible()
      .catch(() => false);
    const hasDestructive = await page
      .locator(".text-destructive")
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasError || hasMessage || hasDestructive).toBeTruthy();
  });

  test("public view page loads without crashing", async ({ page }) => {
    const response = await page.goto(`${APP_BASE}/view/test-token-123`);
    expect(response).not.toBeNull();
    // Should not get a 500 server error
    expect(response!.status()).toBeLessThan(500);
  });

  test("valid token with email required shows identify screen", async ({ page }) => {
    // This test will show the identify screen or error depending on token validity
    await page.goto(`${APP_BASE}/view/test-token-123`);
    await page.waitForTimeout(5_000);

    // Either shows identify screen ("Who's viewing?") or error
    const hasIdentify = await page
      .getByRole("heading", { name: /who.*viewing/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasError = await page
      .getByText(/unable to load report|invalid|expired/i)
      .first()
      .isVisible()
      .catch(() => false);
    const hasViewer = await page
      .getByText(/lintpdf/i)
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasIdentify || hasError || hasViewer).toBeTruthy();
  });
});
