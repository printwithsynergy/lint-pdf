import { test, expect } from "@playwright/test";
import {
  authenticateRole,
  isMcpBackdoorAvailable,
  getEngineApiKey,
  getEngineBase,
  pollJobViaEngine,
} from "../helpers";
import { readFileSync, existsSync } from "fs";
import { resolve } from "path";

const TEST_PDF = resolve(
  __dirname,
  "../../../engine/tests/fixtures/test-sample.pdf",
);

interface ReportInfo {
  // token and url are nullable because the engine now supports an
  // opt-in inline return mode that omits the signed-token URL for
  // text formats (json, xml). Callers asking for the default
  // return="url" still get both fields populated.
  token?: string | null;
  format: string;
  url?: string | null;
  expires_at?: string | null;
  data?: unknown;
  content_type?: string | null;
}

interface ReportResponse {
  reports?: ReportInfo[];
  // Legacy single-report fields (for compatibility)
  token?: string;
  report_id?: string;
  id?: string;
  url?: string;
  format?: string;
  [key: string]: unknown;
}

interface ReportListItem {
  report_id?: string;
  id?: string;
  token?: string;
  format?: string;
  created_at?: string;
  [key: string]: unknown;
}

// Serial mode: tests share closure state (completedJobId, tokens) and must
// run in a single worker so the state persists across describe boundaries.
test.describe.configure({ mode: "serial" });

test.describe("Preflight: Report Generation", () => {
  let engineApiKey: string;
  let engineBase: string;
  let completedJobId: string;
  let reportEndpointAvailable = false;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
    test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

    engineApiKey = getEngineApiKey();
    engineBase = getEngineBase();
    test.skip(!engineApiKey, "Engine API key not available");

    await authenticateRole(request, "owner");

    // Submit a job and wait for completion
    const pdfBuffer = readFileSync(TEST_PDF);
    const submitRes = await request.post(
      `${engineBase}/api/v1/jobs`,
      {
        headers: { Authorization: `Bearer ${engineApiKey}` },
        multipart: {
          file: {
            name: "test-sample.pdf",
            mimeType: "application/pdf",
            buffer: pdfBuffer,
          },
          profile_id: "lintpdf-default",
        },
      },
    );

    expect(
      [200, 201, 202].includes(submitRes.status()),
      `Submit failed: ${submitRes.status()} ${await submitRes.text()}`,
    ).toBe(true);

    const submitData = await submitRes.json();
    completedJobId = submitData.job_id ?? submitData.id;
    expect(completedJobId).toBeTruthy();

    const result = await pollJobViaEngine(
      request,
      completedJobId,
      engineApiKey,
      120_000,
    );
    test.skip(
      result.status !== "complete",
      `Job did not complete: ${result.status}`,
    );

    // Probe report generation endpoint by listing reports for the just-completed job
    const probeRes = await request.get(
      `${engineBase}/api/v1/jobs/${completedJobId}/reports`,
      {
        headers: { Authorization: `Bearer ${engineApiKey}` },
      },
    );
    // 200 = endpoint exists; 404 only if route is missing entirely
    reportEndpointAvailable = probeRes.status() === 200;
  });

  test.describe("HTML report generation", () => {
    let htmlReportToken: string;

    test("POST /api/v1/jobs/{job_id}/reports with html format returns a token", async ({
      request,
    }) => {
      test.skip(!reportEndpointAvailable, "Report generation endpoint not available");

      const res = await request.post(
        `${engineBase}/api/v1/jobs/${completedJobId}/reports`,
        {
          headers: {
            Authorization: `Bearer ${engineApiKey}`,
            "Content-Type": "application/json",
          },
          data: {
            formats: ["html"],
          },
        },
      );

      if (res.status() === 404 || res.status() === 501) {
        reportEndpointAvailable = false;
        test.skip(true, "Report generation not implemented");
        return;
      }

      expect(
        [200, 201, 202].includes(res.status()),
        `Report generation failed: ${res.status()} ${await res.text()}`,
      ).toBe(true);

      const data = (await res.json()) as ReportResponse;
      const reports = data.reports ?? [];
      const htmlReport = reports.find((r) => r.format === "html");
      htmlReportToken = htmlReport?.token ?? "";

      expect(
        htmlReportToken,
        "Report generation returned no html token",
      ).toBeTruthy();
    });

    test("GET /r/{token} returns accessible HTML report (public, no auth)", async ({
      request,
    }) => {
      test.skip(!reportEndpointAvailable, "Report generation endpoint not available");
      test.skip(!htmlReportToken, "No HTML report token available");

      const res = await request.get(`${engineBase}/r/${htmlReportToken}`, {
        headers: {}, // No auth — public endpoint
      });

      expect(
        res.ok(),
        `HTML report not accessible: ${res.status()}`,
      ).toBe(true);

      const contentType = res.headers()["content-type"] ?? "";
      expect(
        contentType.includes("text/html"),
        `Expected text/html content type, got: ${contentType}`,
      ).toBe(true);

      const body = await res.text();
      expect(body.length).toBeGreaterThan(0);
      // Basic check that it looks like HTML
      expect(
        body.includes("<") && body.includes(">"),
        "Response does not appear to be HTML",
      ).toBe(true);
    });
  });

  test.describe("PDF report generation", () => {
    let pdfReportToken: string;

    test("POST /api/v1/jobs/{job_id}/reports with pdf format returns a token", async ({
      request,
    }) => {
      test.skip(!reportEndpointAvailable, "Report generation endpoint not available");

      const res = await request.post(
        `${engineBase}/api/v1/jobs/${completedJobId}/reports`,
        {
          headers: {
            Authorization: `Bearer ${engineApiKey}`,
            "Content-Type": "application/json",
          },
          data: {
            formats: ["pdf"],
          },
        },
      );

      if (res.status() === 404 || res.status() === 501) {
        test.skip(true, "PDF report generation not implemented");
        return;
      }

      expect(
        [200, 201, 202].includes(res.status()),
        `PDF report generation failed: ${res.status()} ${await res.text()}`,
      ).toBe(true);

      const data = (await res.json()) as ReportResponse;
      const reports = data.reports ?? [];
      const pdfReport = reports.find((r) => r.format === "pdf");
      pdfReportToken = pdfReport?.token ?? "";

      expect(pdfReportToken, "No token returned for PDF report").toBeTruthy();
    });

    test("GET /r/{token}.pdf returns accessible PDF report (public)", async ({
      request,
    }) => {
      test.skip(!reportEndpointAvailable, "Report generation endpoint not available");
      test.skip(!pdfReportToken, "No PDF report token available");

      const res = await request.get(
        `${engineBase}/r/${pdfReportToken}.pdf`,
        {
          headers: {}, // No auth — public endpoint
        },
      );

      expect(
        res.ok(),
        `PDF report not accessible: ${res.status()}`,
      ).toBe(true);

      const contentType = res.headers()["content-type"] ?? "";
      expect(
        contentType.includes("application/pdf") ||
          contentType.includes("application/octet-stream"),
        `Expected PDF content type, got: ${contentType}`,
      ).toBe(true);

      const body = await res.body();
      expect(body.length).toBeGreaterThan(0);
      // PDF files start with %PDF
      const header = body.slice(0, 5).toString("utf-8");
      expect(
        header.startsWith("%PDF"),
        `Response does not appear to be a PDF (header: ${header})`,
      ).toBe(true);
    });
  });

  test.describe("Report listing", () => {
    test("GET /api/v1/jobs/{id}/reports lists reports for job", async ({
      request,
    }) => {
      test.skip(!reportEndpointAvailable, "Report generation endpoint not available");

      const res = await request.get(
        `${engineBase}/api/v1/jobs/${completedJobId}/reports`,
        {
          headers: { Authorization: `Bearer ${engineApiKey}` },
        },
      );

      if (res.status() === 404) {
         
        console.log("  [INFO] Report listing endpoint not implemented");
        return;
      }

      expect(res.ok(), `Report listing failed: ${res.status()}`).toBe(true);

      const data = await res.json();
      const reports: ReportListItem[] = Array.isArray(data)
        ? data
        : data.reports ?? [];
      expect(Array.isArray(reports)).toBe(true);

      // We generated at least one report above
      expect(
        reports.length,
        "Expected at least one report for the completed job",
      ).toBeGreaterThan(0);

      for (const report of reports) {
        // List endpoint returns token (not report_id)
        const reportToken = report.token ?? report.report_id ?? report.id;
        expect(reportToken, "Report missing token").toBeTruthy();

        if (report.format) {
          expect(
            ["html", "pdf"],
            `Unexpected report format: ${report.format}`,
          ).toContain(report.format);
        }
      }
    });
  });

  test.describe("Report revocation", () => {
    let revokeToken: string;

    test("generate a report to revoke", async ({ request }) => {
      test.skip(!reportEndpointAvailable, "Report generation endpoint not available");

      const res = await request.post(
        `${engineBase}/api/v1/jobs/${completedJobId}/reports`,
        {
          headers: {
            Authorization: `Bearer ${engineApiKey}`,
            "Content-Type": "application/json",
          },
          data: {
            formats: ["html"],
          },
        },
      );

      test.skip(!res.ok(), "Could not generate report for revocation test");

      const data = (await res.json()) as ReportResponse;
      const reports = data.reports ?? [];
      revokeToken = reports.find((r) => r.format === "html")?.token ?? "";

      expect(revokeToken).toBeTruthy();
    });

    test("DELETE /api/v1/jobs/{job_id}/reports/{token} revokes the report", async ({
      request,
    }) => {
      test.skip(!reportEndpointAvailable, "Report generation endpoint not available");
      test.skip(!revokeToken, "No report token to revoke");

      const res = await request.delete(
        `${engineBase}/api/v1/jobs/${completedJobId}/reports/${revokeToken}`,
        {
          headers: { Authorization: `Bearer ${engineApiKey}` },
        },
      );

      if (res.status() === 404 || res.status() === 501) {
         
        console.log("  [INFO] Report revocation endpoint not implemented");
        return;
      }

      expect(
        [200, 204].includes(res.status()),
        `Report revocation failed: ${res.status()} ${await res.text()}`,
      ).toBe(true);
    });

    test("GET /r/{revoked_token} returns 404 or 410 after revocation", async ({
      request,
    }) => {
      test.skip(!reportEndpointAvailable, "Report generation endpoint not available");
      test.skip(!revokeToken, "No revoked token to check");

      const res = await request.get(`${engineBase}/r/${revokeToken}`, {
        headers: {}, // No auth — public endpoint
      });

      expect(
        [404, 410].includes(res.status()),
        `Expected 404/410 for revoked report, got ${res.status()}`,
      ).toBe(true);
    });
  });

  test.describe("Inline return mode", () => {
    test("POST /reports with return=inline returns JSON data in body", async ({
      request,
    }) => {
      test.skip(!reportEndpointAvailable, "Report generation endpoint not available");

      const res = await request.post(
        `${engineBase}/api/v1/jobs/${completedJobId}/reports`,
        {
          headers: {
            Authorization: `Bearer ${engineApiKey}`,
            "Content-Type": "application/json",
          },
          data: {
            formats: [{ format: "json", return: "inline" }],
          },
        },
      );

      if (res.status() === 404 || res.status() === 501) {
        test.skip(true, "Inline return mode not implemented on this engine build");
        return;
      }

      expect(
        [200, 201].includes(res.status()),
        `Inline report generation failed: ${res.status()} ${await res.text()}`,
      ).toBe(true);

      const data = (await res.json()) as ReportResponse;
      const jsonReport = (data.reports ?? []).find((r) => r.format === "json");
      expect(jsonReport, "No json report in response").toBeTruthy();
      expect(jsonReport?.url, "inline JSON must not carry a hosted url").toBeFalsy();
      expect(jsonReport?.token, "inline JSON must not carry a token").toBeFalsy();
      expect(
        typeof jsonReport?.data === "object" && jsonReport?.data !== null,
        "inline JSON must surface parsed object in data",
      ).toBe(true);
      expect(jsonReport?.content_type).toBe("application/json");
    });

    test("POST /reports rejects return=inline on binary formats (422)", async ({
      request,
    }) => {
      test.skip(!reportEndpointAvailable, "Report generation endpoint not available");

      const res = await request.post(
        `${engineBase}/api/v1/jobs/${completedJobId}/reports`,
        {
          headers: {
            Authorization: `Bearer ${engineApiKey}`,
            "Content-Type": "application/json",
          },
          data: {
            formats: [{ format: "pdf", return: "inline" }],
          },
        },
      );

      expect(
        res.status(),
        `Expected 422 for inline PDF request, got ${res.status()}`,
      ).toBe(422);
    });
  });

  test.describe("Report auth rejection", () => {
    test("POST /api/v1/jobs/{job_id}/reports rejects unauthenticated requests", async ({
      request,
    }) => {
      test.skip(!reportEndpointAvailable, "Report generation endpoint not available");

      const res = await request.post(
        `${engineBase}/api/v1/jobs/${completedJobId}/reports`,
        {
          headers: {
            Authorization: "",
            "Content-Type": "application/json",
          },
          data: {
            formats: ["html"],
          },
        },
      );

      expect(res.ok()).toBe(false);
      expect(
        [401, 403].includes(res.status()),
        `Expected 401/403 for unauthenticated report generation, got ${res.status()}`,
      ).toBe(true);
    });
  });
});
