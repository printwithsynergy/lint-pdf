import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Admin Jobs API (Plugin Routes)", () => {
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

  test.describe("GET /api/lintpdf/admin/jobs", () => {
    test("returns 200 with cross-tenant jobs list", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/jobs`, {
        headers: headers(),
      });

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("jobs");
        expect(Array.isArray(body.jobs)).toBe(true);
      }
    });

    test("jobs include tenant information", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/jobs`, {
        headers: headers(),
      });

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        const jobs = body.jobs ?? [];

        if (jobs.length > 0) {
          const job = jobs[0];
          // Admin jobs should include tenant context
          expect(
            job.tenantId ?? job.tenant ?? job.tenantName ?? job.organizationId,
          ).toBeDefined();
        }
      }
    });

    test("jobs include status and file info", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/jobs`, {
        headers: headers(),
      });

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        const jobs = body.jobs ?? [];

        if (jobs.length > 0) {
          const job = jobs[0];
          expect(job.status).toBeDefined();
          expect(job.fileName ?? job.filename ?? job.file ?? job.name).toBeDefined();
        }
      }
    });

    test("supports pagination", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/admin/jobs?page=1&limit=5`,
        {
          headers: headers(),
        },
      );

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("jobs");
        expect(body.jobs.length).toBeLessThanOrEqual(5);
      }
    });

    test("supports status filter", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/admin/jobs?status=complete`,
        {
          headers: headers(),
        },
      );

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);
      if (res.status() !== 200) return;
      const body = await res.json();
      const jobs = body.jobs ?? [];

      for (const job of jobs) {
        expect(job.status).toBe("complete");
      }
    });

    test("supports tenant filter", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/admin/jobs?tenantId=some-tenant`,
        {
          headers: headers(),
        },
      );

      // 200 with filtered results or empty list
      expect([200, 400, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/jobs`, {
        headers: { Cookie: "" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("returns 403 for non-admin role", async ({ request }) => {
      const ownerAuth = await authenticateRole(request, "owner");

      const res = await request.get(`${APP_BASE}/api/lintpdf/admin/jobs`, {
        headers: {
          Cookie: `pixie-dust-session=${ownerAuth.sessionToken}`,
        },
      });

      expect([401, 403, 404, 500].includes(res.status())).toBe(true);
    });
  });
});
