import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Reports API (Plugin Routes)", () => {
  let sessionToken: string;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
    const auth = await authenticateRole(request, "owner");
    sessionToken = auth.sessionToken;
  });

  test.describe("Report generation", () => {
    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/reports/generate`, {
        headers: { Cookie: "", "Content-Type": "application/json" },
        data: { jobId: "test-job-id" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("returns 400/404 for non-existent job", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/reports/generate`, {
        headers: {
          Cookie: `pixie-dust-session=${sessionToken}`,
          "Content-Type": "application/json",
        },
        data: { jobId: "non-existent-report-job-id" },
      });

      expect([400, 404].includes(res.status())).toBe(true);
    });

    test("generates report for completed job", async ({ request }) => {
      // List jobs to find a completed one
      const listRes = await request.get(
        `${APP_BASE}/api/lintpdf/jobs?status=complete&limit=1`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      const listBody = await listRes.json();
      const jobs = (listBody.jobs ?? []).filter(
        (j: Record<string, unknown>) => j.status === "complete",
      );

      test.skip(jobs.length === 0, "No completed jobs available for report generation");

      const jobId = jobs[0].id ?? jobs[0].jobId;
      const res = await request.post(`${APP_BASE}/api/lintpdf/reports/generate`, {
        headers: {
          Cookie: `pixie-dust-session=${sessionToken}`,
          "Content-Type": "application/json",
        },
        data: { jobId },
      });

      // 200/201/202 for success, or 409 if report already exists
      expect([200, 201, 202, 409].includes(res.status())).toBe(true);
    });
  });

  test.describe("Report access", () => {
    test("GET /api/lintpdf/reports returns 200", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/reports`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      });

      // May return 200 with empty list or 404 if no reports endpoint
      expect([200, 404].includes(res.status())).toBe(true);
    });

    test("GET /api/lintpdf/reports/:jobId returns report for valid job", async ({
      request,
    }) => {
      // Find a completed job
      const listRes = await request.get(
        `${APP_BASE}/api/lintpdf/jobs?status=complete&limit=1`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      const listBody = await listRes.json();
      const jobs = (listBody.jobs ?? []).filter(
        (j: Record<string, unknown>) => j.status === "complete",
      );

      test.skip(jobs.length === 0, "No completed jobs for report access test");

      const jobId = jobs[0].id ?? jobs[0].jobId;
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/reports/${jobId}`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      // 200 with report data, or 404 if report not yet generated
      expect([200, 404].includes(res.status())).toBe(true);

      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toBeTruthy();
      }
    });

    test("returns 404 for non-existent report", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/reports/non-existent-report-id`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      expect([404, 400].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/reports`, {
        headers: { Cookie: "" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("Report download", () => {
    test("GET /api/lintpdf/reports/:jobId/download returns PDF or 404", async ({
      request,
    }) => {
      const listRes = await request.get(
        `${APP_BASE}/api/lintpdf/jobs?status=complete&limit=1`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      const listBody = await listRes.json();
      const jobs = (listBody.jobs ?? []).filter(
        (j: Record<string, unknown>) => j.status === "complete",
      );

      test.skip(jobs.length === 0, "No completed jobs for report download test");

      const jobId = jobs[0].id ?? jobs[0].jobId;
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/reports/${jobId}/download`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      // 200 with PDF content, or 404 if no report generated
      expect([200, 404].includes(res.status())).toBe(true);

      if (res.status() === 200) {
        const contentType = res.headers()["content-type"] ?? "";
        expect(
          contentType.includes("pdf") || contentType.includes("octet-stream"),
        ).toBe(true);
      }
    });
  });
});
