import { test, expect } from "@playwright/test";
import { createAuthenticatedContext, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.nevergrounded.io";

const DASHBOARD_PAGES = [
  { path: "/dashboard/account", name: "Account" },
  { path: "/dashboard/api-keys", name: "API Keys" },
  { path: "/dashboard/billing", name: "Billing" },
  { path: "/dashboard/flight-plans", name: "Flight Plans" },
  { path: "/dashboard/preflight", name: "Preflight" },
  { path: "/dashboard/reports", name: "Reports" },
  { path: "/dashboard/team", name: "Team" },
  { path: "/dashboard/usage", name: "Usage" },
  { path: "/dashboard/waitlist", name: "Waitlist" },
];

test.describe("Dashboard Navigation", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor is not enabled on this environment");
  });

  for (const { path, name } of DASHBOARD_PAGES) {
    test(`${name} page (${path}) loads when authenticated`, async ({
      browser,
    }) => {
      const { context } = await createAuthenticatedContext(browser, APP_BASE);
      const page = await context.newPage();

      const response = await page.goto(path);

      // Page should load without server error
      expect(response).not.toBeNull();
      expect(response!.status()).toBeLessThan(500);

      // Should not redirect to login (we're authenticated)
      const currentUrl = page.url();
      expect(currentUrl).not.toContain("/auth/login");

      await context.close();
    });
  }

  test("Admin page loads for authenticated users", async ({ browser }) => {
    const { context } = await createAuthenticatedContext(browser, APP_BASE);
    const page = await context.newPage();

    const response = await page.goto("/dashboard/admin");

    // Admin page may return 403 for non-admin users, which is acceptable
    expect(response).not.toBeNull();
    expect(response!.status()).toBeLessThan(500);

    await context.close();
  });
});
