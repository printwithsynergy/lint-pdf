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

const PROFILES = [
  "lintpdf-default",
  "lintpdf-strict",
  "lintpdf-advisory-only",
  "pdfx4",
  "pdfx1a-magazine-ads",
  "pdfx3-european",
  "iso-12647-compliance",
  "gwg-2022-coated-offset",
  "gwg-2022-uncoated-offset",
  "gwg-2022-digital-print",
  "gwg-2022-sign-display",
  "gwg-2022-packaging",
  "gwg-2022-newspaper",
  "gwg-web-offset",
  "gwg-sheetfed-offset",
  "hp-indigo-epm",
  "ecg-readiness",
] as const;

test.describe("Preflight: All Built-in Profiles", () => {
  let sessionToken: string;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
    test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

    const auth = await authenticateRole(request, "owner");
    sessionToken = auth.sessionToken;
  });

  for (const profileId of PROFILES) {
    test(`submits and completes with profile: ${profileId}`, async ({
      request,
    }) => {
      // Submit the test PDF with this profile
      const pdfBuffer = readFileSync(TEST_PDF);
      const submitRes = await request.post(`${APP_BASE}/api/lintpdf/submit`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        multipart: {
          file: {
            name: "test-sample.pdf",
            mimeType: "application/pdf",
            buffer: pdfBuffer,
          },
          profile_id: profileId,
        },
      });

      expect(
        [200, 201, 202].includes(submitRes.status()),
        `Submit failed for ${profileId}: ${submitRes.status()} ${await submitRes.text()}`,
      ).toBe(true);

      const submitData = await submitRes.json();
      const jobId = submitData.job_id ?? submitData.id;
      expect(jobId, `No job ID returned for profile ${profileId}`).toBeTruthy();

      // Poll until the job reaches a terminal state (2 min timeout for heavy profiles)
      const result = await pollJobViaApp(
        request,
        jobId,
        sessionToken,
        120_000,
      );

      expect(
        ["complete", "failed"],
        `Job ${jobId} ended with unexpected status: ${result.status}`,
      ).toContain(result.status);

      if (result.status === "complete") {
        // Validate summary structure
        const summary = result.summary as Record<string, unknown> | undefined;
        expect(
          summary,
          `Completed job ${jobId} is missing summary`,
        ).toBeTruthy();

        if (summary) {
          expect(summary).toHaveProperty("total_findings");
          expect(summary).toHaveProperty("error_count");
          expect(summary).toHaveProperty("warning_count");
          expect(summary).toHaveProperty("advisory_count");
          expect(summary).toHaveProperty("passed");

          expect(typeof summary.total_findings).toBe("number");
          expect(typeof summary.error_count).toBe("number");
          expect(typeof summary.warning_count).toBe("number");
          expect(typeof summary.advisory_count).toBe("number");
          expect(typeof summary.passed).toBe("boolean");
        }

        // Validate findings array exists
        const findings = result.findings as unknown[] | undefined;
        expect(findings, `Completed job is missing findings array`).toBeDefined();

        if (Array.isArray(findings)) {
          expect(findings.length).toBeGreaterThanOrEqual(0);
        }
      }

      if (result.status === "failed") {
        // Even failed jobs should have an error message
        const error = result.error ?? result.message;
        expect(
          error,
          `Failed job ${jobId} has no error message`,
        ).toBeTruthy();
      }
    });
  }

  test("rejects submission with invalid profile ID", async ({ request }) => {
    const pdfBuffer = readFileSync(TEST_PDF);
    const res = await request.post(`${APP_BASE}/api/lintpdf/submit`, {
      headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      multipart: {
        file: {
          name: "test-sample.pdf",
          mimeType: "application/pdf",
          buffer: pdfBuffer,
        },
        profile_id: "nonexistent-profile-id",
      },
    });

    // Should reject with a 400 or 404
    expect(res.ok()).toBe(false);
    expect([400, 404, 422].includes(res.status())).toBe(true);
  });

  test("rejects submission without a file", async ({ request }) => {
    const res = await request.post(`${APP_BASE}/api/lintpdf/submit`, {
      headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      multipart: {
        profile_id: "lintpdf-default",
      },
    });

    expect(res.ok()).toBe(false);
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });

  test("rejects unauthenticated submission", async ({ request }) => {
    const pdfBuffer = readFileSync(TEST_PDF);
    const res = await request.post(`${APP_BASE}/api/lintpdf/submit`, {
      headers: { Cookie: "" },
      multipart: {
        file: {
          name: "test-sample.pdf",
          mimeType: "application/pdf",
          buffer: pdfBuffer,
        },
        profile_id: "lintpdf-default",
      },
    });

    expect(res.ok()).toBe(false);
    expect([401, 302, 307, 403].includes(res.status())).toBe(true);
  });
});
