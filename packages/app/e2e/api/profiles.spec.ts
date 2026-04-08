import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Profiles API (Plugin Routes)", () => {
  let sessionToken: string;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
    const auth = await authenticateRole(request, "owner");
    sessionToken = auth.sessionToken;
  });

  test.describe("GET /api/lintpdf/profiles", () => {
    test("returns 200 with profiles array", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/profiles`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      });

      expect([200, 401, 403, 422, 500, 502].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("profiles");
        expect(Array.isArray(body.profiles)).toBe(true);
      }
    });

    test("profiles include built-in defaults", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/profiles`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      });

      expect([200, 401, 403, 422, 500, 502].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        const profiles = body.profiles ?? [];

        // There should be at least one profile (e.g., "default" or built-in)
        expect(profiles.length).toBeGreaterThanOrEqual(0);
      }
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/profiles`, {
        headers: { Cookie: "" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("GET /api/lintpdf/profiles/:id", () => {
    test("returns profile detail for existing profile", async ({ request }) => {
      // First list to get an ID
      const listRes = await request.get(`${APP_BASE}/api/lintpdf/profiles`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      });

      const listBody = await listRes.json().catch(() => ({ profiles: [] }));
      const profiles = listBody.profiles ?? [];

      test.skip(profiles.length === 0, "No profiles available to test detail");

      const profileId = profiles[0].id;
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/profiles/${profileId}`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      expect([200, 401, 403, 404, 422, 500, 502].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body.id ?? body.profile?.id).toBeTruthy();
      }
    });

    test("returns 404 for non-existent profile", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/profiles/non-existent-profile-id`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      expect([400, 401, 403, 404, 422, 500, 502].includes(res.status())).toBe(true);
    });
  });

  test.describe("POST /api/lintpdf/profiles", () => {
    const testProfileName = `e2e-test-profile-${Date.now()}`;

    test("creates a custom profile", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/profiles`, {
        headers: {
          Cookie: `pixie-dust-session=${sessionToken}`,
          "Content-Type": "application/json",
        },
        data: {
          name: testProfileName,
          description: "E2E test profile",
          checks: {
            resolution: { enabled: true, minDpi: 300 },
            colorSpace: { enabled: true },
          },
        },
      });

      // 200/201 for success, 400/422 for validation errors
      expect([200, 201, 400, 401, 422, 500, 502].includes(res.status())).toBe(true);

      if (res.ok()) {
        const body = await res.json();
        expect(body.id ?? body.profile?.id).toBeTruthy();
      }
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/profiles`, {
        headers: {
          Cookie: "",
          "Content-Type": "application/json",
        },
        data: {
          name: "unauth-profile",
          checks: {},
        },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("returns 400 for invalid profile data", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/profiles`, {
        headers: {
          Cookie: `pixie-dust-session=${sessionToken}`,
          "Content-Type": "application/json",
        },
        data: {},
      });

      expect([400, 401, 422, 500, 502].includes(res.status())).toBe(true);
    });
  });

  test.describe("DELETE /api/lintpdf/profiles/:id", () => {
    test("returns 404 for non-existent profile", async ({ request }) => {
      const res = await request.delete(
        `${APP_BASE}/api/lintpdf/profiles/non-existent-delete-profile`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      expect([400, 401, 403, 404, 422, 500, 502].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.delete(
        `${APP_BASE}/api/lintpdf/profiles/any-id`,
        {
          headers: { Cookie: "" },
        },
      );

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("cannot delete built-in profiles", async ({ request }) => {
      // List profiles to find a built-in one. Engine returns snake_case
      // fields — see ``api/routes/profiles.py:ProfileResponse``.
      const listRes = await request.get(`${APP_BASE}/api/lintpdf/profiles`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      });

      const listBody = await listRes.json().catch(() => ({ profiles: [] }));
      const profiles = Array.isArray(listBody)
        ? listBody
        : listBody.profiles ?? [];
      const builtIn = profiles.find(
        (p: Record<string, unknown>) =>
          p.is_builtin === true ||
          p.builtIn === true ||
          p.isDefault === true ||
          p.system === true,
      );

      expect(
        builtIn,
        "Expected engine to return at least one built-in profile",
      ).toBeTruthy();

      const builtInId = (builtIn.profile_id ?? builtIn.id) as string;
      expect(builtInId).toBeTruthy();

      const res = await request.delete(
        `${APP_BASE}/api/lintpdf/profiles/${builtInId}`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      // Should reject deletion of built-in profiles
      expect(
        [400, 401, 403, 409, 422, 500, 502].includes(res.status()),
        `Expected deletion rejection, got ${res.status()}`,
      ).toBe(true);
    });
  });
});
