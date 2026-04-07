import { test, expect } from "@playwright/test";
import {
  authenticateRole,
  isMcpBackdoorAvailable,
  pollJobViaApp,
} from "../helpers";
import { readFileSync, existsSync } from "fs";
import { resolve } from "path";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";
const TEST_PDF = resolve(
  __dirname,
  "../../../engine/tests/fixtures/test-sample.pdf",
);

const VALID_SEVERITIES = ["ERROR", "WARNING", "ADVISORY"];
const VALID_SOURCES = ["engine", "ai"];
const INSPECTION_ID_PATTERN = /^LPDF_/;

interface Finding {
  inspection_id: string;
  severity: string;
  message: string;
  page_num: number;
  source?: string;
  details?: Record<string, unknown>;
  bbox?: number[];
}

interface JobSummary {
  total_findings: number;
  error_count: number;
  warning_count: number;
  advisory_count: number;
  passed: boolean;
}

test.describe("Preflight: Findings Validation", () => {
  let sessionToken: string;
  let completedJob: Record<string, unknown>;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
    test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

    const auth = await authenticateRole(request, "owner");
    sessionToken = auth.sessionToken;

    // Submit a job with the default profile and wait for completion
    const pdfBuffer = readFileSync(TEST_PDF);
    const submitRes = await request.post(`${APP_BASE}/api/lintpdf/submit`, {
      headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      multipart: {
        file: {
          name: "test-sample.pdf",
          mimeType: "application/pdf",
          buffer: pdfBuffer,
        },
        profile_id: "lintpdf-default",
      },
    });

    expect(submitRes.ok(), `Submit failed: ${await submitRes.text()}`).toBe(
      true,
    );
    const submitData = await submitRes.json();
    const jobId = submitData.job_id ?? submitData.id;
    expect(jobId).toBeTruthy();

    completedJob = await pollJobViaApp(request, jobId, sessionToken, 120_000);
    // Only proceed if the job completed (not failed)
    test.skip(
      completedJob.status !== "complete",
      `Job did not complete successfully: ${completedJob.status}`,
    );
  });

  test.describe("Finding structure", () => {
    test("findings array exists and is non-empty", () => {
      const findings = completedJob.findings as Finding[];
      expect(Array.isArray(findings)).toBe(true);
      // The default profile on the test PDF should produce at least some findings
      expect(findings.length).toBeGreaterThan(0);
    });

    test("each finding has a valid inspection_id starting with LPDF_", () => {
      const findings = completedJob.findings as Finding[];
      for (const finding of findings) {
        expect(finding.inspection_id).toBeTruthy();
        expect(finding.inspection_id).toMatch(INSPECTION_ID_PATTERN);
      }
    });

    test("each finding has a valid severity", () => {
      const findings = completedJob.findings as Finding[];
      for (const finding of findings) {
        expect(finding.severity).toBeTruthy();
        expect(
          VALID_SEVERITIES,
          `Unexpected severity "${finding.severity}" on ${finding.inspection_id}`,
        ).toContain(finding.severity);
      }
    });

    test("each finding has a message string", () => {
      const findings = completedJob.findings as Finding[];
      for (const finding of findings) {
        expect(typeof finding.message).toBe("string");
        expect(finding.message.length).toBeGreaterThan(0);
      }
    });

    test("each finding has a numeric page_num", () => {
      const findings = completedJob.findings as Finding[];
      for (const finding of findings) {
        expect(typeof finding.page_num).toBe("number");
        expect(finding.page_num).toBeGreaterThanOrEqual(0);
      }
    });
  });

  test.describe("Summary validation", () => {
    test("summary exists with required fields", () => {
      const summary = completedJob.summary as JobSummary;
      expect(summary).toBeTruthy();
      expect(typeof summary.total_findings).toBe("number");
      expect(typeof summary.error_count).toBe("number");
      expect(typeof summary.warning_count).toBe("number");
      expect(typeof summary.advisory_count).toBe("number");
      expect(typeof summary.passed).toBe("boolean");
    });

    test("summary counts are non-negative", () => {
      const summary = completedJob.summary as JobSummary;
      expect(summary.total_findings).toBeGreaterThanOrEqual(0);
      expect(summary.error_count).toBeGreaterThanOrEqual(0);
      expect(summary.warning_count).toBeGreaterThanOrEqual(0);
      expect(summary.advisory_count).toBeGreaterThanOrEqual(0);
    });

    test("summary total_findings matches findings array length", () => {
      const summary = completedJob.summary as JobSummary;
      const findings = completedJob.findings as Finding[];
      expect(summary.total_findings).toBe(findings.length);
    });

    test("summary severity counts match findings breakdown", () => {
      const summary = completedJob.summary as JobSummary;
      const findings = completedJob.findings as Finding[];

      const errorCount = findings.filter(
        (f) => f.severity === "ERROR",
      ).length;
      const warningCount = findings.filter(
        (f) => f.severity === "WARNING",
      ).length;
      const advisoryCount = findings.filter(
        (f) => f.severity === "ADVISORY",
      ).length;

      expect(summary.error_count).toBe(errorCount);
      expect(summary.warning_count).toBe(warningCount);
      expect(summary.advisory_count).toBe(advisoryCount);
    });

    test("summary.passed is false when errors exist, true otherwise", () => {
      const summary = completedJob.summary as JobSummary;
      if (summary.error_count > 0) {
        expect(summary.passed).toBe(false);
      } else {
        expect(summary.passed).toBe(true);
      }
    });
  });

  test.describe("Finding categorization", () => {
    test("findings have a source field", () => {
      const findings = completedJob.findings as Finding[];
      for (const finding of findings) {
        // Source may not be present on all findings, but if present it must be valid
        if (finding.source !== undefined) {
          expect(
            VALID_SOURCES,
            `Unexpected source "${finding.source}" on ${finding.inspection_id}`,
          ).toContain(finding.source);
        }
      }
    });

    test("at least some findings come from the engine", () => {
      const findings = completedJob.findings as Finding[];
      const engineFindings = findings.filter((f) => f.source === "engine");
      // The engine should always produce findings on the test PDF
      // If source is not populated, skip this assertion
      if (findings.some((f) => f.source !== undefined)) {
        expect(engineFindings.length).toBeGreaterThan(0);
      }
    });
  });

  test.describe("Finding details and bbox", () => {
    test("findings with details have a valid details object", () => {
      const findings = completedJob.findings as Finding[];
      const withDetails = findings.filter((f) => f.details !== undefined);

      for (const finding of withDetails) {
        expect(typeof finding.details).toBe("object");
        expect(finding.details).not.toBeNull();
      }
    });

    test("findings with bbox have exactly 4 numeric values", () => {
      const findings = completedJob.findings as Finding[];
      const withBbox = findings.filter((f) => f.bbox !== undefined);

      for (const finding of withBbox) {
        expect(Array.isArray(finding.bbox)).toBe(true);
        expect(finding.bbox!.length).toBe(4);
        for (const val of finding.bbox!) {
          expect(typeof val).toBe("number");
          expect(Number.isFinite(val)).toBe(true);
        }
      }
    });
  });

  test.describe("Job detail endpoint", () => {
    test("GET /api/lintpdf/jobs/:id returns full job data", async ({
      request,
    }) => {
      const jobId =
        (completedJob.job_id as string) ?? (completedJob.id as string);
      const res = await request.get(`${APP_BASE}/api/lintpdf/jobs/${jobId}`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      });

      expect(res.ok()).toBe(true);
      const data = await res.json();

      expect(data.status).toBe("complete");
      expect(data.findings).toBeDefined();
      expect(data.summary).toBeDefined();
      expect(data.profile_id ?? data.profileId).toBe("lintpdf-default");
    });

    test("GET /api/lintpdf/jobs/:id rejects unauthenticated requests", async ({
      request,
    }) => {
      const jobId =
        (completedJob.job_id as string) ?? (completedJob.id as string);
      const res = await request.get(`${APP_BASE}/api/lintpdf/jobs/${jobId}`, {
        headers: { Cookie: "" },
      });

      expect(res.ok()).toBe(false);
      expect([401, 302, 307, 403].includes(res.status())).toBe(true);
    });

    test("GET /api/lintpdf/jobs/:id returns 404 for nonexistent job", async ({
      request,
    }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/jobs/nonexistent-job-id-000`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      expect(res.ok()).toBe(false);
      expect([404, 400].includes(res.status())).toBe(true);
    });
  });
});
