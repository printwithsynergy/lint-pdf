import { test, expect } from "@playwright/test";

test.describe("Beta Waitlist Flow", () => {
  test("beta join page loads", async ({ page }) => {
    await page.goto("/beta/join");
    await expect(page).toHaveTitle(/Grounded/i);
  });

  test("waitlist form is visible and has required fields", async ({ page }) => {
    await page.goto("/beta/join");

    // Check form fields exist
    const emailInput = page.getByLabel(/email/i).or(page.locator('input[type="email"]'));
    await expect(emailInput.first()).toBeVisible();
  });

  test("waitlist form submits successfully", async ({ page }) => {
    await page.goto("/beta/join");

    const uniqueEmail = `pw-test-${Date.now()}@example.com`;

    // Fill form
    const emailInput = page.getByLabel(/email/i).or(page.locator('input[type="email"]'));
    await emailInput.first().fill(uniqueEmail);

    // Fill name if present
    const nameInput = page.getByLabel(/name/i).or(page.locator('input[name="name"]'));
    if (await nameInput.first().isVisible()) {
      await nameInput.first().fill("Playwright Test");
    }

    // Submit
    const submitBtn = page.getByRole("button", { name: /join|submit|sign up/i });
    await submitBtn.first().click();

    // Wait for success feedback
    await page.waitForTimeout(2000);

    // Check for success message or redirect
    const success = page.getByText(/thank|success|submitted|waitlist/i);
    await expect(success.first()).toBeVisible({ timeout: 5000 });
  });
});
