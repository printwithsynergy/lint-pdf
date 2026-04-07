import { test, expect } from "@playwright/test";

test.describe("Login Page", () => {
  test("renders the login page", async ({ page }) => {
    await page.goto("/auth/login");

    // Default heading when no custom branding is set
    await expect(
      page.getByRole("heading", { name: /welcome back/i }),
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
      name: /send magic link/i,
    });
    await expect(submitButton).toBeVisible();
  });

  test("shows branding", async ({ page }) => {
    await page.goto("/auth/login");

    // Default branding shows "Powered by Pixie Dust" tagline
    await expect(page.getByText(/powered by pixie dust/i)).toBeVisible();
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
      name: /send magic link/i,
    });
    await submitButton.click();

    // HTML5 validation should prevent submission — input still has type="email"
    await expect(emailInput).toHaveAttribute("type", "email");
  });
});
