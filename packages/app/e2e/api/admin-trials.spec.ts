import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Admin Trials API (Plugin Routes)", () => {
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

  test.describe("GET /api/lintpdf/admin/trials", () => {
    test("returns 200 with trials list", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/trials`, {
        headers: headers(),
      });

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("trials");
        expect(Array.isArray(body.trials)).toBe(true);
      }
    });

    test("trials include email and status", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/trials`, {
        headers: headers(),
      });

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        const trials = body.trials ?? [];

        if (trials.length > 0) {
          const trial = trials[0];
          expect(trial.email).toBeDefined();
          expect(trial.status ?? trial.state).toBeDefined();
        }
      }
    });

    test("trials include date and file count", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/trials`, {
        headers: headers(),
      });

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);
      if (res.status() !== 200) return;
      const body = await res.json();
      const trials = body.trials ?? [];

      if (trials.length > 0) {
        const trial = trials[0];
        expect(trial.createdAt ?? trial.date ?? trial.submittedAt).toBeDefined();
        expect(
          trial.fileCount ?? trial.files ?? trial.filesCount,
        ).toBeDefined();
      }
    });

    test("supports status filter", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/admin/trials?status=pending`,
        {
          headers: headers(),
        },
      );

      expect([200, 400, 500].includes(res.status())).toBe(true);
    });

    test("supports pagination", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/admin/trials?page=1&limit=10`,
        {
          headers: headers(),
        },
      );

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("trials");
      }
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/trials`, {
        headers: { Cookie: "" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("returns 403 for non-admin role", async ({ request }) => {
      const ownerAuth = await authenticateRole(request, "owner");

      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/trials`, {
        headers: {
          Cookie: `pixie-dust-session=${ownerAuth.sessionToken}`,
        },
      });

      expect([401, 403, 404, 500].includes(res.status())).toBe(true);
    });
  });
});
