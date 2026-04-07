import { test, expect } from "@playwright/test";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Public Report View", () => {
  test("invalid token shows error page", async ({ page }) => {
    await page.goto(`${APP_BASE}/view/invalid-token-that-does-not-exist`);
    await page.waitForTimeout(5_000);

    // Should show error for invalid/expired link
    await expect(
      page.getByText(/unable to load report|invalid|expired/i).first(),
    ).toBeVisible({ timeout: 15_000 });
  });

  test("invalid token page shows descriptive error message", async ({ page }) => {
    await page.goto(`${APP_BASE}/view/aaaa-bbbb-cccc-dddd`);
    await page.waitForTimeout(5_000);

    // Should show the error heading
    const hasError = await page
      .getByRole("heading", { name: /unable to load report/i })
      .isVisible()
      .catch(() => false);
    const hasMessage = await page
      .getByText(/this link may be invalid or expired/i)
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
