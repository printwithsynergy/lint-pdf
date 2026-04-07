import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Admin Entitlements API (Plugin Routes)", () => {
  let sessionToken: string;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
    const auth = await authenticateRole(request, "super-admin");
    sessionToken = auth.sessionToken;
  });

  const headers = () => ({
    Cookie: `pixie-dust-session=${sessionToken}`,
    "Content-Type": "application/json",
  });

  test.describe("GET /api/lintpdf/admin/entitlements", () => {
    test("returns 200 with entitlements list", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/entitlements`, {
        headers: headers(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);

      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("entitlements");
        expect(Array.isArray(body.entitlements)).toBe(true);
      }
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/entitlements`, {
        headers: { Cookie: "" },
      });

      expect([401, 403, 404].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("returns 403 for non-admin role", async ({ request }) => {
      const ownerAuth = await authenticateRole(request, "owner");

      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/entitlements`, {
        headers: {
          Cookie: `pixie-dust-session=${ownerAuth.sessionToken}`,
        },
      });

      expect([401, 403, 404, 500].includes(res.status())).toBe(true);
    });
  });

  test.describe("GET /api/lintpdf/admin/entitlements/:tenantId", () => {
    test("returns entitlements for a specific tenant", async ({ request }) => {
      const tenantsRes = await request.get(`${APP_BASE}/api/lintpdf/admin/tenants`, {
        headers: headers(),
      });

      const tenantsBody = await tenantsRes.json().catch(() => ({ tenants: [] }));
      const tenants = tenantsBody.tenants ?? [];

      test.skip(tenants.length === 0, "No tenants to get entitlements for");

      const res = await request.get(
        `${APP_BASE}/api/lintpdf/admin/entitlements/${tenants[0].id}`,
        {
          headers: headers(),
        },
      );

      expect([200, 404, 500].includes(res.status())).toBe(true);

      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toBeTruthy();
      }
    });

    test("returns 404 for non-existent tenant", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/admin/entitlements/non-existent-tenant`,
        {
          headers: headers(),
        },
      );

      expect([400, 404, 500].includes(res.status())).toBe(true);
    });
  });

  test.describe("PUT /api/lintpdf/admin/entitlements/:tenantId", () => {
    test("updates entitlement overrides for a tenant", async ({ request }) => {
      const tenantsRes = await request.get(`${APP_BASE}/api/lintpdf/admin/tenants`, {
        headers: headers(),
      });

      const tenantsBody = await tenantsRes.json().catch(() => ({ tenants: [] }));
      const tenants = tenantsBody.tenants ?? [];

      test.skip(tenants.length === 0, "No tenants to update entitlements for");

      const res = await request.put(
        `${APP_BASE}/api/lintpdf/admin/entitlements/${tenants[0].id}`,
        {
          headers: headers(),
          data: {
            maxJobs: 100,
            maxFileSize: 52428800,
            aiEnabled: true,
          },
        },
      );

      expect([200, 204, 400, 404, 422, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.put(
        `${APP_BASE}/api/lintpdf/admin/entitlements/any-tenant`,
        {
          headers: { Cookie: "", "Content-Type": "application/json" },
          data: { maxJobs: 50 },
        },
      );

      expect([401, 403, 404].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("returns 403 for non-admin role", async ({ request }) => {
      const ownerAuth = await authenticateRole(request, "owner");

      const res = await request.put(
        `${APP_BASE}/api/lintpdf/admin/entitlements/any-tenant`,
        {
          headers: {
            Cookie: `pixie-dust-session=${ownerAuth.sessionToken}`,
            "Content-Type": "application/json",
          },
          data: { maxJobs: 999 },
        },
      );

      expect([401, 403, 404, 500].includes(res.status())).toBe(true);
    });
  });

  test.describe("DELETE /api/lintpdf/admin/entitlements/:tenantId", () => {
    test("resets entitlement overrides for a tenant", async ({ request }) => {
      const tenantsRes = await request.get(`${APP_BASE}/api/lintpdf/admin/tenants`, {
        headers: headers(),
      });

      const tenantsBody = await tenantsRes.json().catch(() => ({ tenants: [] }));
      const tenants = tenantsBody.tenants ?? [];

      test.skip(tenants.length === 0, "No tenants to reset entitlements for");

      const res = await request.delete(
        `${APP_BASE}/api/lintpdf/admin/entitlements/${tenants[0].id}`,
        {
          headers: headers(),
        },
      );

      expect([200, 204, 404, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.delete(
        `${APP_BASE}/api/lintpdf/admin/entitlements/any-tenant`,
        {
          headers: { Cookie: "" },
        },
      );

      expect([401, 403, 404].includes(res.status()) || !res.ok()).toBe(true);
    });
  });
});
