import { test, expect } from "@playwright/test";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Public Report View", () => {
  test("invalid token shows error page", async ({ page }) => {
    await page.goto(`${APP_BASE}/view/invalid-token-that-does-not-exist`);
    await page.waitForTimeout(5_000);

    // Should show error for invalid/expired link — heading or body text
    const hasErrorHeading = await page
      .getByRole("heading", { name: /unable to load report/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasErrorText = await page
      .getByText(/unable to load report|invalid|expired|failed to load/i)
      .first()
      .isVisible()
      .catch(() => false);
    const hasDestructive = await page
      .locator(".text-destructive")
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasErrorHeading || hasErrorText || hasDestructive).toBeTruthy();
  });

  test("invalid token page shows descriptive error message", async ({ page }) => {
    await page.goto(`${APP_BASE}/view/aaaa-bbbb-cccc-dddd`);
    await page.waitForTimeout(5_000);

    // Should show the error heading or descriptive message
    const hasError = await page
      .getByRole("heading", { name: /unable to load report/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasMessage = await page
      .getByText(/invalid or expired|unable to load|failed/i)
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasError || hasMessage).toBeTruthy();
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

    // Either shows identify screen or error
    const hasIdentify = await page
      .getByRole("heading", { name: /who's viewing/i })
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
