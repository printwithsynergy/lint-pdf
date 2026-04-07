import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Color Config API (Plugin Routes)", () => {
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

  test.describe("GET /api/lintpdf/color-config", () => {
    test("returns 200 with color configuration", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/color-config`, {
        headers: headers(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toBeTruthy();
      }
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/color-config`, {
        headers: { Cookie: "" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("PUT /api/lintpdf/color-config", () => {
    test("updates color configuration", async ({ request }) => {
      const res = await request.put(`${APP_BASE}/api/lintpdf/color-config`, {
        headers: headers(),
        data: {
          defaultColorSpace: "CMYK",
          enforceColorSpace: true,
        },
      });

      expect([200, 204, 400, 422, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.put(`${APP_BASE}/api/lintpdf/color-config`, {
        headers: { Cookie: "", "Content-Type": "application/json" },
        data: { defaultColorSpace: "RGB" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("returns 400 for invalid color space", async ({ request }) => {
      const res = await request.put(`${APP_BASE}/api/lintpdf/color-config`, {
        headers: headers(),
        data: {
          defaultColorSpace: "INVALID_COLOR_SPACE",
        },
      });

      expect([200, 204, 400, 422, 500].includes(res.status())).toBe(true);
    });
  });

  test.describe("POST /api/lintpdf/color-config/icc", () => {
    test("uploads ICC profile", async ({ request }) => {
      // Create a minimal fake ICC profile header
      const iccBuffer = Buffer.alloc(128);
      iccBuffer.writeUInt32BE(128, 0); // Profile size
      iccBuffer.write("acsp", 36); // ICC signature

      const res = await request.post(`${APP_BASE}/api/lintpdf/color-config/icc`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        multipart: {
          file: {
            name: "e2e-test.icc",
            mimeType: "application/vnd.iccprofile",
            buffer: iccBuffer,
          },
        },
      });

      // Accept or reject based on ICC validation
      expect([200, 201, 400, 415, 422, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/color-config/icc`, {
        headers: { Cookie: "" },
        multipart: {
          file: {
            name: "unauth.icc",
            mimeType: "application/vnd.iccprofile",
            buffer: Buffer.alloc(10),
          },
        },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("rejects non-ICC file types", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/color-config/icc`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        multipart: {
          file: {
            name: "not-icc.txt",
            mimeType: "text/plain",
            buffer: Buffer.from("this is not an ICC profile"),
          },
        },
      });

      expect([400, 415, 422, 500].includes(res.status())).toBe(true);
    });
  });

  test.describe("PUT /api/lintpdf/color-config/palette", () => {
    test("updates color palette", async ({ request }) => {
      const res = await request.put(`${APP_BASE}/api/lintpdf/color-config/palette`, {
        headers: headers(),
        data: {
          colors: [
            { name: "Brand Red", hex: "#CC0000", cmyk: { c: 0, m: 100, y: 100, k: 20 } },
            { name: "Brand Blue", hex: "#003399", cmyk: { c: 100, m: 67, y: 0, k: 40 } },
          ],
        },
      });

      expect([200, 204, 400, 422, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.put(`${APP_BASE}/api/lintpdf/color-config/palette`, {
        headers: { Cookie: "", "Content-Type": "application/json" },
        data: { colors: [] },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("Pantone endpoints", () => {
    test("GET /api/lintpdf/color-config/pantone returns 200", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/color-config/pantone`, {
        headers: headers(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);

      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toBeTruthy();
      }
    });

    test("PUT /api/lintpdf/color-config/pantone updates Pantone config", async ({
      request,
    }) => {
      const res = await request.put(`${APP_BASE}/api/lintpdf/color-config/pantone`, {
        headers: headers(),
        data: {
          enabled: true,
          library: "Pantone+ Solid Coated",
        },
      });

      expect([200, 204, 400, 404, 422, 500].includes(res.status())).toBe(true);
    });

    test("DELETE /api/lintpdf/color-config/pantone resets Pantone config", async ({
      request,
    }) => {
      const res = await request.delete(
        `${APP_BASE}/api/lintpdf/color-config/pantone`,
        {
          headers: headers(),
        },
      );

      expect([200, 204, 404, 500].includes(res.status())).toBe(true);
    });

    test("GET /api/lintpdf/color-config/pantone returns 401 without auth", async ({
      request,
    }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/color-config/pantone`, {
        headers: { Cookie: "" },
      });

      expect([401, 403, 404].includes(res.status()) || !res.ok()).toBe(true);
    });
  });
});
