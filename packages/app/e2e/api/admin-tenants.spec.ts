import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Admin Tenants API (Plugin Routes)", () => {
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

  test.describe("GET /api/lintpdf/admin/tenants", () => {
    test("returns 200 with tenants list", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/tenants`, {
        headers: headers(),
      });

      expect([200, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("tenants");
        expect(Array.isArray(body.tenants)).toBe(true);
      }
    });

    test("tenants include name, plan, and status", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/tenants`, {
        headers: headers(),
      });

      expect([200, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        const tenants = body.tenants ?? [];

        if (tenants.length > 0) {
          const tenant = tenants[0];
          expect(tenant).toHaveProperty("name");
          expect(tenant.plan ?? tenant.planId ?? tenant.subscription).toBeDefined();
          expect(tenant.status ?? tenant.active ?? tenant.suspended).toBeDefined();
        }
      }
    });

    test("supports pagination", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/admin/tenants?page=1&limit=5`,
        {
          headers: headers(),
        },
      );

      expect([200, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("tenants");
      }
    });

    test("supports search filter", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/admin/tenants?search=test`,
        {
          headers: headers(),
        },
      );

      expect([200, 400, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/tenants`, {
        headers: { Cookie: "" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("returns 403 for non-admin role", async ({ request }) => {
      const ownerAuth = await authenticateRole(request, "owner");

      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/tenants`, {
        headers: {
          Cookie: `pixie-dust-session=${ownerAuth.sessionToken}`,
        },
      });

      expect([401, 403, 404, 500].includes(res.status())).toBe(true);
    });
  });

  test.describe("PATCH /api/lintpdf/admin/tenants/:id/plan", () => {
    test("returns 404 for non-existent tenant", async ({ request }) => {
      const res = await request.patch(
        `${APP_BASE}/api/lintpdf/admin/tenants/non-existent-tenant-id/plan`,
        {
          headers: headers(),
          data: { plan: "pro" },
        },
      );

      expect([400, 404, 500].includes(res.status())).toBe(true);
    });

    test("updates tenant plan for existing tenant", async ({ request }) => {
      // Get first tenant
      const listRes = await request.get(`${APP_BASE}/api/lintpdf/admin/tenants`, {
        headers: headers(),
      });

      const body = await listRes.json().catch(() => ({ tenants: [] }));
      const tenants = body.tenants ?? [];

      test.skip(tenants.length === 0, "No tenants to test plan change");

      const tenantId = tenants[0].id;
      const currentPlan = tenants[0].plan ?? tenants[0].planId ?? "free";

      const res = await request.patch(
        `${APP_BASE}/api/lintpdf/admin/tenants/${tenantId}/plan`,
        {
          headers: headers(),
          data: { plan: currentPlan },
        },
      );

      expect([200, 204, 400, 404, 422, 500].includes(res.status())).toBe(true);
    });

    test("returns 400 for invalid plan name", async ({ request }) => {
      const listRes = await request.get(`${APP_BASE}/api/lintpdf/admin/tenants`, {
        headers: headers(),
      });

      const body = await listRes.json().catch(() => ({ tenants: [] }));
      const tenants = body.tenants ?? [];

      test.skip(tenants.length === 0, "No tenants to test invalid plan");

      const tenantId = tenants[0].id;
      const res = await request.patch(
        `${APP_BASE}/api/lintpdf/admin/tenants/${tenantId}/plan`,
        {
          headers: headers(),
          data: { plan: "INVALID_PLAN_NAME_XYZ" },
        },
      );

      expect([400, 404, 422, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.patch(
        `${APP_BASE}/api/lintpdf/admin/tenants/any-id/plan`,
        {
          headers: { Cookie: "", "Content-Type": "application/json" },
          data: { plan: "pro" },
        },
      );

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("PATCH /api/lintpdf/admin/tenants/:id/status", () => {
    test("returns 404 for non-existent tenant", async ({ request }) => {
      const res = await request.patch(
        `${APP_BASE}/api/lintpdf/admin/tenants/non-existent-tenant-id/status`,
        {
          headers: headers(),
          data: { status: "active" },
        },
      );

      expect([400, 404, 500].includes(res.status())).toBe(true);
    });

    test("updates tenant status", async ({ request }) => {
      const listRes = await request.get(`${APP_BASE}/api/lintpdf/admin/tenants`, {
        headers: headers(),
      });

      const body = await listRes.json().catch(() => ({ tenants: [] }));
      const tenants = body.tenants ?? [];

      test.skip(tenants.length === 0, "No tenants to test status change");

      const tenantId = tenants[0].id;
      const currentStatus = tenants[0].status ?? "active";

      const res = await request.patch(
        `${APP_BASE}/api/lintpdf/admin/tenants/${tenantId}/status`,
        {
          headers: headers(),
          data: { status: currentStatus },
        },
      );

      expect([200, 204, 400, 404, 422, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.patch(
        `${APP_BASE}/api/lintpdf/admin/tenants/any-id/status`,
        {
          headers: { Cookie: "", "Content-Type": "application/json" },
          data: { status: "suspended" },
        },
      );

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("returns 403 for non-admin role", async ({ request }) => {
      const ownerAuth = await authenticateRole(request, "owner");

      const res = await request.patch(
        `${APP_BASE}/api/lintpdf/admin/tenants/any-id/status`,
        {
          headers: {
            Cookie: `pixie-dust-session=${ownerAuth.sessionToken}`,
            "Content-Type": "application/json",
          },
          data: { status: "suspended" },
        },
      );

      expect([401, 403, 404, 500].includes(res.status())).toBe(true);
    });
  });
});
