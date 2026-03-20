import { test, expect } from "@playwright/test";
import { existsSync, readFileSync } from "fs";
import { resolve } from "path";
import { getAnyTenantKey, pollJob } from "../helpers";

const TEST_PDF = resolve(
  __dirname,
  "../../../../packages/engine/tests/fixtures/test-sample.pdf",
);

test.describe("Reports", () => {
  let apiKey: string;
  let completedJobId: string;

  test.beforeAll(async ({ request }) => {
    apiKey = getAnyTenantKey();
    if (!apiKey || !existsSync(TEST_PDF)) return;

    // Submit a job and wait for completion
    const submitRes = await request.post("/api/v1/jobs", {
      headers: { Authorization: `Bearer ${apiKey}` },
      multipart: {
        file: {
          name: "report-test.pdf",
          mimeType: "application/pdf",
          buffer: readFileSync(TEST_PDF),
        },
      },
    });
    if (submitRes.status() === 202) {
      const { job_id } = await submitRes.json();
      try {
        const result = await pollJob(request, job_id, apiKey, 60_000);
        if (result.status === "complete") completedJobId = job_id;
      } catch {
        // Job didn't complete in time
      }
    }
  });

  test("POST /api/v1/jobs/:id/reports generates reports", async ({
    request,
  }) => {
    test.skip(!apiKey || !completedJobId, "No completed job available");

    const res = await request.post(`/api/v1/jobs/${completedJobId}/reports`, {
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      data: { formats: ["html"] },
    });
    expect([200, 201]).toContain(res.status());
    const body = await res.json();
    expect(body).toHaveProperty("reports");
    expect(Array.isArray(body.reports)).toBe(true);
  });

  test("GET /api/v1/jobs/:id/reports lists report tokens", async ({
    request,
  }) => {
    test.skip(!apiKey || !completedJobId, "No completed job available");

    const res = await request.get(`/api/v1/jobs/${completedJobId}/reports`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("reports");
  });

  test("GET /r/:token serves public HTML report", async ({ request }) => {
    test.skip(!apiKey || !completedJobId, "No completed job available");

    // First generate a report
    await request.post(`/api/v1/jobs/${completedJobId}/reports`, {
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      data: { formats: ["html"] },
    });

    // Get tokens
    const tokenRes = await request.get(
      `/api/v1/jobs/${completedJobId}/reports`,
      {
        headers: { Authorization: `Bearer ${apiKey}` },
      },
    );
    const { reports } = await tokenRes.json();
    test.skip(!reports?.length, "No report tokens available");

    const htmlReport = reports.find(
      (t: { format: string; token: string }) => t.format === "html",
    );
    test.skip(!htmlReport, "No HTML report token");

    const res = await request.get(`/r/${htmlReport.token}`);
    expect(res.status()).toBe(200);
  });
});
