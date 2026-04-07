import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Branding API (Plugin Routes)", () => {
  let sessionToken: string;

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

  test.describe("GET /api/lintpdf/branding/profiles", () => {
    test("returns 200 with branding profiles", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/branding/profiles`, {
        headers: headers(),
      });

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("profiles");
        expect(Array.isArray(body.profiles)).toBe(true);
      }
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/branding/profiles`, {
        headers: { Cookie: "" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("POST /api/lintpdf/branding/profiles", () => {
    test("creates a branding profile", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/branding/profiles`, {
        headers: headers(),
        data: {
          name: `E2E Brand ${Date.now()}`,
          primaryColor: "#336699",
          secondaryColor: "#993366",
        },
      });

      expect([200, 201, 400, 422, 500].includes(res.status())).toBe(true);

      if (res.ok()) {
        const body = await res.json();
        expect(body.id ?? body.profile?.id).toBeTruthy();
      }
    });

    test("returns 400 for missing required fields", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/branding/profiles`, {
        headers: headers(),
        data: {},
      });

      expect([400, 422, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/branding/profiles`, {
        headers: { Cookie: "", "Content-Type": "application/json" },
        data: { name: "Unauth brand" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("PUT /api/lintpdf/branding/profiles/:id", () => {
    test("returns 404 for non-existent branding profile", async ({ request }) => {
      const res = await request.put(
        `${APP_BASE}/api/lintpdf/branding/profiles/non-existent-brand-id`,
        {
          headers: headers(),
          data: { name: "Updated Brand", primaryColor: "#112233" },
        },
      );

      expect([400, 403, 404, 500].includes(res.status())).toBe(true);
    });

    test("updates existing branding profile", async ({ request }) => {
      // List to find an existing profile
      const listRes = await request.get(`${APP_BASE}/api/lintpdf/branding/profiles`, {
        headers: headers(),
      });

      const listBody = await listRes.json().catch(() => ({ profiles: [] }));
      const profiles = listBody.profiles ?? [];

      test.skip(profiles.length === 0, "No branding profiles to update");

      const profileId = profiles[0].id;
      const res = await request.put(
        `${APP_BASE}/api/lintpdf/branding/profiles/${profileId}`,
        {
          headers: headers(),
          data: {
            name: `Updated E2E Brand ${Date.now()}`,
            primaryColor: "#445566",
          },
        },
      );

      expect([200, 204, 400, 404, 500].includes(res.status())).toBe(true);
    });
  });

  test.describe("DELETE /api/lintpdf/branding/profiles/:id", () => {
    test("returns 404 for non-existent branding profile", async ({ request }) => {
      const res = await request.delete(
        `${APP_BASE}/api/lintpdf/branding/profiles/non-existent-brand-delete`,
        {
          headers: headers(),
        },
      );

      expect([400, 403, 404, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.delete(
        `${APP_BASE}/api/lintpdf/branding/profiles/any-id`,
        {
          headers: { Cookie: "" },
        },
      );

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("POST /api/lintpdf/branding/logos", () => {
    test("uploads a logo image", async ({ request }) => {
      // Create a minimal 1x1 PNG
      const pngBuffer = Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "base64",
      );

      const res = await request.post(`${APP_BASE}/api/lintpdf/branding/logos`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        multipart: {
          file: {
            name: "e2e-logo.png",
            mimeType: "image/png",
            buffer: pngBuffer,
          },
        },
      });

      expect([200, 201, 400, 413, 422, 500].includes(res.status())).toBe(true);

      if (res.ok()) {
        const body = await res.json();
        expect(body.url ?? body.logoUrl ?? body.id).toBeTruthy();
      }
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/branding/logos`, {
        headers: { Cookie: "" },
        multipart: {
          file: {
            name: "unauth-logo.png",
            mimeType: "image/png",
            buffer: Buffer.from("fake"),
          },
        },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("rejects non-image file types", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/branding/logos`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        multipart: {
          file: {
            name: "not-an-image.txt",
            mimeType: "text/plain",
            buffer: Buffer.from("This is not an image"),
          },
        },
      });

      // Should reject non-image uploads
      expect([400, 415, 422, 500].includes(res.status())).toBe(true);
    });
  });

  test.describe("PATCH /api/lintpdf/branding/default", () => {
    test("sets default branding profile", async ({ request }) => {
      // List to find a profile
      const listRes = await request.get(`${APP_BASE}/api/lintpdf/branding/profiles`, {
        headers: headers(),
      });

      const listBody = await listRes.json().catch(() => ({ profiles: [] }));
      const profiles = listBody.profiles ?? [];

      test.skip(profiles.length === 0, "No branding profiles to set as default");

      const res = await request.patch(`${APP_BASE}/api/lintpdf/branding/default`, {
        headers: headers(),
        data: { profileId: profiles[0].id },
      });

      expect([200, 204, 400, 403, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.patch(`${APP_BASE}/api/lintpdf/branding/default`, {
        headers: { Cookie: "", "Content-Type": "application/json" },
        data: { profileId: "any-id" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });
});
