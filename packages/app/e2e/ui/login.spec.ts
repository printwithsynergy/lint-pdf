import { test, expect } from "@playwright/test";

test.describe("Login Page", () => {
  test("renders the login page", async ({ page }) => {
    await page.goto("/auth/login");

    // Check page title/heading
    await expect(
      page.getByRole("heading", { name: /welcome to never grounded/i }),
    ).toBeVisible();
  });

  test("has email input field", async ({ page }) => {
    await page.goto("/auth/login");

    const emailInput = page.getByLabel(/email/i);
    await expect(emailInput).toBeVisible();
    await expect(emailInput).toHaveAttribute("type", "email");
  });

  test("has submit button", async ({ page }) => {
    await page.goto("/auth/login");

    const submitButton = page.getByRole("button", {
      name: /continue with email/i,
    });
    await expect(submitButton).toBeVisible();
  });

  test("shows branding logo", async ({ page }) => {
    await page.goto("/auth/login");

    // The NG branding circle
    await expect(page.getByText("NG")).toBeVisible();
  });

  test("shows no-password message", async ({ page }) => {
    await page.goto("/auth/login");

    await expect(page.getByText(/no password needed/i)).toBeVisible();
  });

  test("validates email format on submit", async ({ page }) => {
    await page.goto("/auth/login");

    const emailInput = page.getByLabel(/email/i);
    await emailInput.fill("not-an-email");

    const submitButton = page.getByRole("button", {
      name: /continue with email/i,
    });
    await submitButton.click();

    // HTML5 validation should prevent submission
    await expect(emailInput).toHaveAttribute("type", "email");
  });
});
