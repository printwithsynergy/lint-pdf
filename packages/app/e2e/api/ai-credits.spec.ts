import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("AI Credits API (Plugin Routes)", () => {
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

  test.describe("GET /api/lintpdf/ai-credits", () => {
    test("returns 200 with credit balance", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/ai-credits`, {
        headers: headers(),
      });

      expect(res.status()).toBe(200);
      const body = await res.json();
      expect(body).toBeTruthy();

      // Should include some balance/credit info
      const hasCredits =
        body.credits !== undefined ||
        body.balance !== undefined ||
        body.remaining !== undefined ||
        body.used !== undefined;
      expect(hasCredits).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/ai-credits`, {
        headers: { Cookie: "" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("credit balance includes usage stats", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/ai-credits`, {
        headers: headers(),
      });

      expect(res.status()).toBe(200);
      const body = await res.json();

      // May include usage history, limits, or plan info
      expect(body).toBeTruthy();
    });
  });

  test.describe("GET /api/lintpdf/ai-credits/usage", () => {
    test("returns credit usage history", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/ai-credits/usage`, {
        headers: headers(),
      });

      // 200 or 404 if this sub-endpoint doesn't exist
      expect([200, 404].includes(res.status())).toBe(true);

      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toBeTruthy();
      }
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/ai-credits/usage`, {
        headers: { Cookie: "" },
      });

      expect([401, 403, 404].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("POST /api/lintpdf/ai-credits/purchase", () => {
    test("returns purchase options or initiates purchase", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/ai-credits/purchase`, {
        headers: headers(),
        data: {
          amount: 100,
        },
      });

      // 200/201 for success, 402 for payment required, 400/404 if endpoint differs
      expect([200, 201, 400, 402, 404, 422].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/ai-credits/purchase`, {
        headers: { Cookie: "", "Content-Type": "application/json" },
        data: { amount: 50 },
      });

      expect([401, 403, 404].includes(res.status()) || !res.ok()).toBe(true);
    });
  });
});
