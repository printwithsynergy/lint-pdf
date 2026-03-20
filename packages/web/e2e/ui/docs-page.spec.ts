import { test, expect } from "@playwright/test";

test.describe("Documentation Page", () => {
  test("docs page loads", async ({ page }) => {
    await page.goto("/docs");
    await expect(page).toHaveTitle(/LintPDF/i);
  });

  test("docs page has content", async ({ page }) => {
    await page.goto("/docs");
    // Wait for main content to render
    const main = page.locator("main");
    await expect(main).toBeVisible();
    // Should have some text content
    const text = await main.textContent();
    expect(text?.length).toBeGreaterThan(50);
  });
});
