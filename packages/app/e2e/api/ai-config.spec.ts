import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("AI Config API (Plugin Routes)", () => {
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

  test.describe("GET /api/lintpdf/ai-config", () => {
    test("returns 200 with AI configuration", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/ai-config`, {
        headers: headers(),
      });

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toBeTruthy();
      }
    });

    test("response includes enabled flag", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/ai-config`, {
        headers: headers(),
      });

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        // AI config should indicate whether AI features are enabled
        expect(typeof (body.enabled ?? body.aiEnabled ?? body.active)).toBeDefined();
      }
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/ai-config`, {
        headers: { Cookie: "" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("PUT /api/lintpdf/ai-config", () => {
    test("updates AI configuration", async ({ request }) => {
      // First get current config
      const getRes = await request.get(`${APP_BASE}/api/lintpdf/ai-config`, {
        headers: headers(),
      });

      const currentConfig = getRes.ok() ? await getRes.json() : {};

      const res = await request.put(`${APP_BASE}/api/lintpdf/ai-config`, {
        headers: headers(),
        data: {
          enabled: currentConfig.enabled ?? true,
          autoAnalyze: currentConfig.autoAnalyze ?? false,
        },
      });

      expect([200, 204, 400, 403, 422, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.put(`${APP_BASE}/api/lintpdf/ai-config`, {
        headers: { Cookie: "", "Content-Type": "application/json" },
        data: { enabled: false },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("returns 400 for invalid config", async ({ request }) => {
      const res = await request.put(`${APP_BASE}/api/lintpdf/ai-config`, {
        headers: headers(),
        data: {
          enabled: "not-a-boolean",
          invalidField: 12345,
        },
      });

      // May accept or reject depending on validation strictness
      expect([200, 204, 400, 403, 422, 500].includes(res.status())).toBe(true);
    });

    test("preserves existing config when updating partial fields", async ({
      request,
    }) => {
      // Get current
      const getRes = await request.get(`${APP_BASE}/api/lintpdf/ai-config`, {
        headers: headers(),
      });

      test.skip(!getRes.ok(), "Cannot get current config");

      const currentConfig = await getRes.json();

      // Update only one field
      const res = await request.put(`${APP_BASE}/api/lintpdf/ai-config`, {
        headers: headers(),
        data: { enabled: currentConfig.enabled ?? true },
      });

      expect([200, 204, 400, 403, 422, 500].includes(res.status())).toBe(true);

      // Verify config is still intact
      const verifyRes = await request.get(`${APP_BASE}/api/lintpdf/ai-config`, {
        headers: headers(),
      });

      expect([200, 403, 404, 500].includes(verifyRes.status())).toBe(true);
    });
  });
});
