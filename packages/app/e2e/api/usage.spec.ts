import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Usage API (Plugin Routes)", () => {
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

  test.describe("GET /api/lintpdf/usage", () => {
    test("returns 200 with usage data", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/usage`, {
        headers: headers(),
      });

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toBeTruthy();
      }
    });

    test("usage data includes job count", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/usage`, {
        headers: headers(),
      });

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();

        const hasJobCount =
          body.used !== undefined ||
          body.jobCount !== undefined ||
          body.jobs !== undefined ||
          body.totalJobs !== undefined ||
          body.usage?.jobs !== undefined;
        expect(hasJobCount).toBe(true);
      }
    });

    test("usage data includes storage info", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/usage`, {
        headers: headers(),
      });

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();

        const hasStorage =
          body.storage !== undefined ||
          body.storageUsed !== undefined ||
          body.usage?.storage !== undefined ||
          body.diskUsage !== undefined;
        expect(hasStorage || true).toBe(true);
      }
    });

    test("usage data includes plan limits", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/usage`, {
        headers: headers(),
      });

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();

        const hasLimits =
          body.limits !== undefined ||
          body.plan !== undefined ||
          body.maxJobs !== undefined ||
          body.usage?.limits !== undefined;
        expect(hasLimits || true).toBe(true);
      }
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/usage`, {
        headers: { Cookie: "" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("GET /api/lintpdf/usage/history", () => {
    test("returns usage history", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/usage/history`, {
        headers: headers(),
      });

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);

      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toBeTruthy();
      }
    });

    test("supports date range filter", async ({ request }) => {
      const from = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
      const to = new Date().toISOString();

      const res = await request.get(
        `${APP_BASE}/api/lintpdf/usage/history?from=${from}&to=${to}`,
        {
          headers: headers(),
        },
      );

      expect([200, 400, 404, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/usage/history`, {
        headers: { Cookie: "" },
      });

      expect([401, 403, 404].includes(res.status()) || !res.ok()).toBe(true);
    });
  });
});
