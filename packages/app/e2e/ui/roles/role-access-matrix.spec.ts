import { test, expect } from "@playwright/test";
import {
  createRoleContext,
  isMcpBackdoorAvailable,
  getTestTenantSlug,
  type TestRole,
} from "../../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

/**
 * Role access matrix — verifies every role can or cannot access each dashboard page.
 *
 * Pages with permission requirements enforce server-side role checks via layout.tsx.
 * Restricted users are redirected to /dashboard.
 */

type AccessLevel = "allowed" | "blocked";

interface PageRule {
  path: string;
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

const ALLOWED_ALL: Record<TestRole, AccessLevel> = {
  "super-admin": "allowed",
  owner: "allowed",
  admin: "allowed",
  operator: "allowed",
  member: "allowed",
  viewer: "allowed",
};

const ADMIN_OWNER_SA: Record<TestRole, AccessLevel> = {
  "super-admin": "allowed",
  owner: "allowed",
  admin: "allowed",
  operator: "blocked",
  member: "blocked",
  viewer: "blocked",
};

const SA_ONLY: Record<TestRole, AccessLevel> = {
  "super-admin": "allowed",
  owner: "blocked",
  admin: "blocked",
  operator: "blocked",
  member: "blocked",
  viewer: "blocked",
};

function buildPageRules(): PageRule[] {
  const slug = getTestTenantSlug();
  return [
    { path: "/dashboard", label: "Dashboard home", access: ALLOWED_ALL },
    { path: `/dashboard/${slug}`, label: "Tenant dashboard", access: ALLOWED_ALL },
    { path: "/dashboard/preflight", label: "Preflight", access: ALLOWED_ALL },
    { path: "/dashboard/rulesets", label: "Rulesets", access: ALLOWED_ALL },
    { path: "/dashboard/api-keys", label: "API Keys", access: ADMIN_OWNER_SA },
    { path: "/dashboard/team", label: "Team", access: ALLOWED_ALL },
    { path: "/dashboard/team/invite", label: "Team Invite", access: ADMIN_OWNER_SA },
    { path: "/dashboard/billing", label: "Billing", access: ADMIN_OWNER_SA },
    { path: "/dashboard/webhooks", label: "Webhooks", access: ADMIN_OWNER_SA },
    { path: "/dashboard/endpoints", label: "Endpoints", access: ADMIN_OWNER_SA },
    { path: "/dashboard/account", label: "Account", access: ADMIN_OWNER_SA },
    { path: "/dashboard/account/ai", label: "Account AI", access: ADMIN_OWNER_SA },
    { path: "/dashboard/account/settings", label: "Account Settings", access: ADMIN_OWNER_SA },
    { path: "/dashboard/account/branding", label: "Account Branding", access: ADMIN_OWNER_SA },
    { path: "/dashboard/account/color", label: "Account Color", access: ADMIN_OWNER_SA },
    { path: "/dashboard/usage", label: "Usage", access: ALLOWED_ALL },
    { path: "/dashboard/reports", label: "Reports", access: ALLOWED_ALL },
    { path: "/dashboard/profile", label: "Profile", access: ALLOWED_ALL },
    { path: "/dashboard/waitlist", label: "Waitlist", access: ALLOWED_ALL },
    { path: "/dashboard/admin", label: "Admin Hub", access: SA_ONLY },
    { path: "/dashboard/admin/tenants", label: "Admin Tenants", access: SA_ONLY },
    { path: "/dashboard/admin/jobs", label: "Admin Jobs", access: SA_ONLY },
    { path: "/dashboard/admin/trials", label: "Admin Trials", access: SA_ONLY },
    { path: "/dashboard/admin/health", label: "Admin Health", access: SA_ONLY },
    { path: "/dashboard/admin/appearance", label: "Admin Appearance", access: SA_ONLY },
    { path: "/dashboard/admin/branding", label: "Admin Branding", access: SA_ONLY },
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
      const expected = pageRule.access[role];

      test(`${expected === "allowed" ? "can" : "cannot"} access ${pageRule.label} (${pageRule.path})`, async ({
        browser,
      }) => {
        const { context } = await createRoleContext(browser, APP_BASE, role);
        const page = await context.newPage();

        const response = await page.goto(pageRule.path, {
          waitUntil: "domcontentloaded",
          timeout: 30_000,
        });

        const status = response?.status() ?? 0;

        if (expected === "allowed") {
          // Page should load without server error
          expect(status, `Expected ${pageRule.path} to load for ${role}, got ${status}`).toBeLessThan(500);

          // Should NOT have been redirected to login
          expect(page.url()).not.toMatch(/\/auth\/login/);
        } else {
          // Blocked: expect redirect to /dashboard (the permission layout redirects there)
          const currentUrl = page.url();
          const isRedirected =
            /\/auth\/login/.test(currentUrl) ||
            (currentUrl.endsWith("/dashboard") || currentUrl.endsWith("/dashboard/"));

          expect(
            isRedirected,
            `Expected ${pageRule.path} to be blocked for ${role}. URL: ${currentUrl}, status: ${status}`,
          ).toBeTruthy();
        }

        await context.close();
      });
    }
  });
}
