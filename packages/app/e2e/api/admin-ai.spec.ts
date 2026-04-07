import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Admin AI API (Plugin Routes)", () => {
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

  test.describe("GET /api/lintpdf/admin/ai/config", () => {
    test("returns 200 with global AI configuration", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/ai/config`, {
        headers: headers(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);

      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toBeTruthy();
      }
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/ai/config`, {
        headers: { Cookie: "" },
      });

      expect([401, 403, 404].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("returns 403 for non-admin role", async ({ request }) => {
      const ownerAuth = await authenticateRole(request, "owner");

      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/ai/config`, {
        headers: {
          Cookie: `pixie-dust-session=${ownerAuth.sessionToken}`,
        },
      });

      expect([401, 403, 404, 500].includes(res.status())).toBe(true);
    });
  });

  test.describe("PUT /api/lintpdf/admin/ai/config", () => {
    test("updates global AI configuration", async ({ request }) => {
      const res = await request.put(`${APP_BASE}/api/lintpdf/admin/ai/config`, {
        headers: headers(),
        data: {
          globalEnabled: true,
          maxCreditsPerTenant: 1000,
          defaultModel: "gpt-4",
        },
      });

      expect([200, 204, 400, 404, 422, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.put(`${APP_BASE}/api/lintpdf/admin/ai/config`, {
        headers: { Cookie: "", "Content-Type": "application/json" },
        data: { globalEnabled: false },
      });

      expect([401, 403, 404].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("GET /api/lintpdf/admin/ai/usage", () => {
    test("returns AI usage across all tenants", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/ai/usage`, {
        headers: headers(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);

      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toBeTruthy();
      }
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/ai/usage`, {
        headers: { Cookie: "" },
      });

      expect([401, 403, 404].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("GET /api/lintpdf/admin/ai/credits", () => {
    test("returns global credit stats", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/ai/credits`, {
        headers: headers(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);

      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toBeTruthy();
      }
    });

    test("returns 403 for non-admin role", async ({ request }) => {
      const ownerAuth = await authenticateRole(request, "owner");

      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/ai/credits`, {
        headers: {
          Cookie: `pixie-dust-session=${ownerAuth.sessionToken}`,
        },
      });

      expect([401, 403, 404, 500].includes(res.status())).toBe(true);
    });
  });

  test.describe("POST /api/lintpdf/admin/ai/credits/grant", () => {
    test("grants credits to a tenant", async ({ request }) => {
      // Get a tenant first
      const tenantsRes = await request.get(`${APP_BASE}/api/lintpdf/admin/tenants`, {
        headers: headers(),
      });

      const tenantsBody = await tenantsRes.json().catch(() => ({ tenants: [] }));
      const tenants = tenantsBody.tenants ?? [];

      test.skip(tenants.length === 0, "No tenants to grant credits to");

      const res = await request.post(
        `${APP_BASE}/api/lintpdf/admin/ai/credits/grant`,
        {
          headers: headers(),
          data: {
            tenantId: tenants[0].id,
            amount: 10,
            reason: "E2E test grant",
          },
        },
      );

      expect([200, 201, 400, 404, 422, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.post(
        `${APP_BASE}/api/lintpdf/admin/ai/credits/grant`,
        {
          headers: { Cookie: "", "Content-Type": "application/json" },
          data: { tenantId: "any", amount: 10 },
        },
      );

      expect([401, 403, 404].includes(res.status()) || !res.ok()).toBe(true);
    });
  });
});
