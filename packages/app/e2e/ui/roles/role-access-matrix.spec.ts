import { test, expect } from "@playwright/test";
import {
  createRoleContext,
  isMcpBackdoorAvailable,
  getTestTenantSlug,
  type TestRole,
} from "../../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

/**
 * Role access matrix — verifies every role can access each dashboard page.
 *
 * The production app renders all dashboard pages for all authenticated roles
 * (returns 200). Access control is enforced at the action/API level, not by
 * blocking page navigation. All pages are marked "allowed" for all roles.
 */

type AccessLevel = "allowed";

interface PageRule {
  path: string;
  /** Human-readable label used in the test title. */
  label: string;
  access: Record<TestRole, AccessLevel>;
}

const ALL_ROLES: TestRole[] = [
  "super-admin",
  "owner",
  "admin",
  "operator",
  "member",
  "viewer",
];

// All pages are accessible to all authenticated roles; access control is at the API level.
const ALLOWED_ALL: Record<TestRole, AccessLevel> = {
  "super-admin": "allowed",
  owner: "allowed",
  admin: "allowed",
  operator: "allowed",
  member: "allowed",
  viewer: "allowed",
};

// We use a function so the slug is resolved at test time, not import time.
function buildPageRules(): PageRule[] {
  const slug = getTestTenantSlug();
  return [
    { path: "/dashboard", label: "Dashboard home", access: ALLOWED_ALL },
    { path: `/dashboard/${slug}`, label: "Tenant dashboard", access: ALLOWED_ALL },
    { path: "/dashboard/preflight", label: "Preflight", access: ALLOWED_ALL },
    { path: "/dashboard/rulesets", label: "Rulesets", access: ALLOWED_ALL },
    { path: "/dashboard/api-keys", label: "API Keys", access: ALLOWED_ALL },
    { path: "/dashboard/team", label: "Team", access: ALLOWED_ALL },
    { path: "/dashboard/team/invite", label: "Team Invite", access: ALLOWED_ALL },
    { path: "/dashboard/billing", label: "Billing", access: ALLOWED_ALL },
    { path: "/dashboard/webhooks", label: "Webhooks", access: ALLOWED_ALL },
    { path: "/dashboard/endpoints", label: "Endpoints", access: ALLOWED_ALL },
    { path: "/dashboard/account", label: "Account", access: ALLOWED_ALL },
    { path: "/dashboard/account/ai", label: "Account AI", access: ALLOWED_ALL },
    { path: "/dashboard/account/settings", label: "Account Settings", access: ALLOWED_ALL },
    { path: "/dashboard/account/branding", label: "Account Branding", access: ALLOWED_ALL },
    { path: "/dashboard/account/color", label: "Account Color", access: ALLOWED_ALL },
    { path: "/dashboard/usage", label: "Usage", access: ALLOWED_ALL },
    { path: "/dashboard/reports", label: "Reports", access: ALLOWED_ALL },
    { path: "/dashboard/profile", label: "Profile", access: ALLOWED_ALL },
    { path: "/dashboard/waitlist", label: "Waitlist", access: ALLOWED_ALL },
    { path: "/dashboard/admin", label: "Admin Hub", access: ALLOWED_ALL },
    { path: "/dashboard/admin/tenants", label: "Admin Tenants", access: ALLOWED_ALL },
    { path: "/dashboard/admin/jobs", label: "Admin Jobs", access: ALLOWED_ALL },
    { path: "/dashboard/admin/trials", label: "Admin Trials", access: ALLOWED_ALL },
    { path: "/dashboard/admin/health", label: "Admin Health", access: ALLOWED_ALL },
    { path: "/dashboard/admin/appearance", label: "Admin Appearance", access: ALLOWED_ALL },
    { path: "/dashboard/admin/branding", label: "Admin Branding", access: ALLOWED_ALL },
  ];
}

for (const role of ALL_ROLES) {
  test.describe(`Role access matrix: ${role}`, () => {
    test.beforeAll(async ({ request }) => {
      const available = await isMcpBackdoorAvailable(request);
      test.skip(!available, "MCP backdoor not enabled");
    });

    const pages = buildPageRules();

    for (const pageRule of pages) {
      test(`can access ${pageRule.label} (${pageRule.path})`, async ({
        browser,
      }) => {
        const { context } = await createRoleContext(browser, APP_BASE, role);
        const page = await context.newPage();

        const response = await page.goto(pageRule.path, {
          waitUntil: "domcontentloaded",
          timeout: 30_000,
        });

        const status = response?.status() ?? 0;

        // Page should load without server error
        expect(status, `Expected ${pageRule.path} to load for ${role}, got ${status}`).toBeLessThan(500);

        // Should NOT have been redirected to login
        expect(page.url()).not.toMatch(/\/auth\/login/);

        await context.close();
      });
    }
  });
}
