import { test, expect } from "@playwright/test";
import { createRoleContext, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Waitlist Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("page loads with heading", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/waitlist");
    await expect(
      page.locator("main").getByRole("heading", { name: /waitlist/i }).first(),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("shows waitlist description", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/waitlist");
    await expect(
      page.getByText(/manage waitlist entries and promotions/i),
    ).toBeVisible({ timeout: 15_000 });
    await context.close();
  });

  test("page loads without server error", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    const response = await page.goto("/dashboard/waitlist");
    expect(response).not.toBeNull();
    expect(response!.status()).toBeLessThan(500);
    const url = page.url();
    expect(url).not.toContain("/auth/login");
    await context.close();
  });
});
