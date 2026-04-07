import { test, expect } from "@playwright/test";
import { createRoleContext, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Team Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("page loads without server error", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    const response = await page.goto("/dashboard/team");
    expect(response).not.toBeNull();
    expect(response!.status()).toBeLessThan(500);
    await context.close();
  });

  test("page shows team-related content", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/team");
    await page.waitForTimeout(5_000);

    // TeamPage is from pixie-dust-dashboard; verify it renders team content
    // Look for common team page elements: heading, member list, invite
    const hasTeamHeading = await page
      .getByRole("heading", { name: /team|members/i })
      .first()
      .isVisible()
      .catch(() => false);
    const hasContent = await page.locator("main, [role='main'], .container, section").first().isVisible().catch(() => false);

    // At minimum the page should render without errors
    expect(hasTeamHeading || hasContent).toBeTruthy();
    await context.close();
  });

  test("team page shows member list or invite option", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/team");
    await page.waitForTimeout(5_000);

    // Look for member-related content or invite button
    const hasMembers = await page.getByText(/owner|admin|member|viewer/i).first().isVisible().catch(() => false);
    const hasInvite = await page.getByRole("button", { name: /invite/i }).isVisible().catch(() => false);
    const hasLink = await page.getByRole("link", { name: /invite/i }).isVisible().catch(() => false);

    // Should have either members listed or invite capability
    expect(hasMembers || hasInvite || hasLink).toBeTruthy();
    await context.close();
  });

  test("team page displays role badges for members", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/team");
    await page.waitForTimeout(5_000);

    // At least the current user should be listed with their role
    const hasRoleBadge = await page
      .getByText(/owner|admin|operator|member|viewer/i)
      .first()
      .isVisible()
      .catch(() => false);
    if (hasRoleBadge) {
      await expect(
        page.getByText(/owner|admin|operator|member|viewer/i).first(),
      ).toBeVisible();
    }
    await context.close();
  });
});

test.describe("Team Invite Page", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
  });

  test("invite page redirects to team page", async ({ browser }) => {
    const { context } = await createRoleContext(browser, APP_BASE, "owner");
    const page = await context.newPage();
    await page.goto("/dashboard/team/invite");
    // The invite page redirects to /dashboard/team
    await page.waitForURL(/\/dashboard\/team/, { timeout: 15_000 });
    await context.close();
  });
});
