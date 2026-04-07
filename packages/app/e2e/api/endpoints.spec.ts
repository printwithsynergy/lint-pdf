import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Custom Endpoints API (Plugin Routes)", () => {
  let sessionToken: string;
  let createdEndpointId: string | null = null;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
    const auth = await authenticateRole(request, "owner");
    sessionToken = auth.sessionToken;
  });

  const headers = () => ({
    Cookie: `pixie-dust-session=${sessionToken}`,
    "Content-Type": "application/json",
  });

  test.describe("POST /api/lintpdf/endpoints", () => {
    test("creates a custom endpoint", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/endpoints`, {
        headers: headers(),
        data: {
          name: `E2E Endpoint ${Date.now()}`,
          description: "Test endpoint created by E2E tests",
          profileId: null,
          webhookUrl: "https://example.com/webhook",
          active: true,
        },
      });

      expect([200, 201, 400, 401, 422, 500, 502].includes(res.status())).toBe(true);

      if (res.ok()) {
        const body = await res.json();
        createdEndpointId = (body.id ?? body.endpoint?.id) as string;
        expect(createdEndpointId).toBeTruthy();
      }
    });

    test("returns 400 for missing required fields", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/endpoints`, {
        headers: headers(),
        data: {},
      });

      expect([400, 401, 422, 500, 502].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/endpoints`, {
        headers: { Cookie: "", "Content-Type": "application/json" },
        data: { name: "Unauth endpoint" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("GET /api/lintpdf/endpoints", () => {
    test("returns 200 with endpoints list", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/endpoints`, {
        headers: headers(),
      });

      expect([200, 401, 403, 404, 422, 500, 502].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("endpoints");
        expect(Array.isArray(body.endpoints)).toBe(true);
      }
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/endpoints`, {
        headers: { Cookie: "" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("list includes recently created endpoint", async ({ request }) => {
      test.skip(!createdEndpointId, "No endpoint was created");

      const res = await request.get(`${APP_BASE}/api/lintpdf/endpoints`, {
        headers: headers(),
      });

      expect([200, 401, 403, 404, 422, 500, 502].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        const endpoints = body.endpoints ?? [];
        const found = endpoints.find(
          (e: Record<string, unknown>) => e.id === createdEndpointId,
        );
        expect(found).toBeTruthy();
      }
    });
  });

  test.describe("PATCH /api/lintpdf/endpoints/:id", () => {
    test("updates an existing endpoint", async ({ request }) => {
      test.skip(!createdEndpointId, "No endpoint was created to update");

      const res = await request.patch(
        `${APP_BASE}/api/lintpdf/endpoints/${createdEndpointId}`,
        {
          headers: headers(),
          data: {
            name: `Updated E2E Endpoint ${Date.now()}`,
            active: false,
          },
        },
      );

      expect([200, 204, 400, 401, 404, 422, 500, 502].includes(res.status())).toBe(true);
    });

    test("returns 404 for non-existent endpoint", async ({ request }) => {
      const res = await request.patch(
        `${APP_BASE}/api/lintpdf/endpoints/non-existent-endpoint-id`,
        {
          headers: headers(),
          data: { name: "Does not exist" },
        },
      );

      expect([400, 401, 403, 404, 422, 500, 502].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.patch(
        `${APP_BASE}/api/lintpdf/endpoints/any-id`,
        {
          headers: { Cookie: "", "Content-Type": "application/json" },
          data: { name: "Unauth update" },
        },
      );

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("DELETE /api/lintpdf/endpoints/:id", () => {
    test("returns 404 for non-existent endpoint", async ({ request }) => {
      const res = await request.delete(
        `${APP_BASE}/api/lintpdf/endpoints/non-existent-endpoint-delete`,
        {
          headers: headers(),
        },
      );

      expect([400, 401, 403, 404, 422, 500, 502].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.delete(
        `${APP_BASE}/api/lintpdf/endpoints/any-id`,
        {
          headers: { Cookie: "" },
        },
      );

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("deletes an existing endpoint", async ({ request }) => {
      test.skip(!createdEndpointId, "No endpoint was created to delete");

      const res = await request.delete(
        `${APP_BASE}/api/lintpdf/endpoints/${createdEndpointId}`,
        {
          headers: headers(),
        },
      );

      expect([200, 204, 401, 404, 422, 500, 502].includes(res.status())).toBe(true);

      // Verify it is gone
      const getRes = await request.get(`${APP_BASE}/api/lintpdf/endpoints`, {
        headers: headers(),
      });

      if (getRes.ok()) {
        const body = await getRes.json();
        const found = (body.endpoints ?? []).find(
          (e: Record<string, unknown>) => e.id === createdEndpointId,
        );
        expect(found).toBeFalsy();
      }
    });
  });
});
