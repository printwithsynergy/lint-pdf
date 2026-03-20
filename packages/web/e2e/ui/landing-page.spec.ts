import { test, expect } from "@playwright/test";

test.describe("Landing Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("page loads with correct title", async ({ page }) => {
    await expect(page).toHaveTitle(/LintPDF/i);
  });

  test("header renders with navigation", async ({ page }) => {
    const header = page.locator("header");
    await expect(header).toBeVisible();
  });

  test("hero section is visible", async ({ page }) => {
    // Look for main heading or hero content
    const heroHeading = page.locator("h1").first();
    await expect(heroHeading).toBeVisible();
  });

  test("features section exists", async ({ page }) => {
    // Scroll to features and verify
    const features = page.getByText(/features/i).first();
    await expect(features).toBeVisible();
  });

  test("pricing section shows plans", async ({ page }) => {
    // Look for pricing content
    const pricing = page.getByText(/pricing/i).first();
    await expect(pricing).toBeVisible();

    // Verify plan names appear
    await expect(page.getByText(/free/i).first()).toBeVisible();
    await expect(page.getByText(/starter/i).first()).toBeVisible();
    await expect(page.getByText(/pro/i).first()).toBeVisible();
  });

  test("footer renders", async ({ page }) => {
    const footer = page.locator("footer");
    await expect(footer).toBeVisible();
  });

  test("Get Started button has correct href", async ({ page }) => {
    const cta = page.getByRole("link", { name: /get started/i }).first();
    await expect(cta).toBeVisible();
    const href = await cta.getAttribute("href");
    expect(href).toBeTruthy();
  });
});
