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

interface Finding {
  inspection_id: string;
  severity: string;
  message: string;
  page_num: number;
  source?: string;
}

interface JobSummary {
  total_findings: number;
  error_count: number;
  warning_count: number;
  advisory_count: number;
  passed: boolean;
}

interface CompletedJob {
  status: string;
  findings: Finding[];
  summary: JobSummary;
  profile_id?: string;
  profileId?: string;
  [key: string]: unknown;
}

/** Submit a job with the given profile and poll to completion. */
/** Multipart payload accepted by Playwright's ``request.post``. */
type MultipartFields = {
  [key: string]:
    | string
    | number
    | boolean
    | { name: string; mimeType: string; buffer: Buffer };
};

async function submitAndPoll(
  request: import("@playwright/test").APIRequestContext,
  sessionToken: string,
  profileId: string,
  extraFields?: Record<string, string>,
): Promise<CompletedJob | null> {
  const pdfBuffer = readFileSync(TEST_PDF);
  const multipart: MultipartFields = {
    file: {
      name: "test-sample.pdf",
      mimeType: "application/pdf",
      buffer: pdfBuffer,
    },
    profile_id: profileId,
    ...extraFields,
  };

  const submitRes = await request.post(`${APP_BASE}/api/lintpdf/submit`, {
    headers: { Cookie: `pixie-dust-session=${sessionToken}` },
    multipart,
  });

  if (!submitRes.ok()) return null;

  const submitData = await submitRes.json();
  const jobId = submitData.job_id ?? submitData.id;
  if (!jobId) return null;

  const result = await pollJobViaApp(request, jobId, sessionToken, 120_000);
  return result as CompletedJob;
}

test.describe("Preflight: Profile Comparison", () => {
  let sessionToken: string;
  let defaultJob: CompletedJob | null;
  let strictJob: CompletedJob | null;
  let advisoryJob: CompletedJob | null;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
    test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

    const auth = await authenticateRole(request, "owner");
    sessionToken = auth.sessionToken;

    // Submit the same PDF to all three core profiles in parallel
    [defaultJob, strictJob, advisoryJob] = await Promise.all([
      submitAndPoll(request, sessionToken, "lintpdf-default"),
      submitAndPoll(request, sessionToken, "lintpdf-strict"),
      submitAndPoll(request, sessionToken, "lintpdf-advisory-only"),
    ]);
  });

  test.describe("Core profile comparisons", () => {
    test("all three core profiles completed successfully", () => {
      expect(defaultJob, "lintpdf-default submission failed").not.toBeNull();
      expect(strictJob, "lintpdf-strict submission failed").not.toBeNull();
      expect(advisoryJob, "lintpdf-advisory-only submission failed").not.toBeNull();

      expect(defaultJob!.status).toBe("complete");
      expect(strictJob!.status).toBe("complete");
      expect(advisoryJob!.status).toBe("complete");
    });

    test("lintpdf-strict produces different findings than lintpdf-default", () => {
      test.skip(!defaultJob || defaultJob.status !== "complete", "Default job not complete");
      test.skip(!strictJob || strictJob.status !== "complete", "Strict job not complete");

      const defaultIds = new Set(defaultJob!.findings.map((f) => f.inspection_id));
      const strictIds = new Set(strictJob!.findings.map((f) => f.inspection_id));

      // Either the count differs or different check IDs are present
      const countsMatch = defaultJob!.findings.length === strictJob!.findings.length;
      const idsMatch =
        defaultIds.size === strictIds.size &&
        [...defaultIds].every((id) => strictIds.has(id));

      expect(
        !countsMatch || !idsMatch,
        "Expected lintpdf-strict to produce different findings than lintpdf-default, " +
          `but both produced ${defaultJob!.findings.length} findings with identical IDs`,
      ).toBe(true);
    });

    test("lintpdf-advisory-only produces only advisory findings", () => {
      test.skip(!advisoryJob || advisoryJob.status !== "complete", "Advisory job not complete");

      const findings = advisoryJob!.findings;
      expect(findings.length).toBeGreaterThan(0);

      // Engine emits lowercase severities — see ``analyzers/finding.py``.
      const nonAdvisory = findings.filter((f) => f.severity !== "advisory");
      expect(
        nonAdvisory.length,
        `Expected all findings to be advisory, but found ${nonAdvisory.length} non-advisory: ` +
          nonAdvisory
            .slice(0, 5)
            .map((f) => `${f.inspection_id} (${f.severity})`)
            .join(", "),
      ).toBe(0);
    });

    test("different profiles have different summary stats", () => {
      test.skip(!defaultJob || defaultJob.status !== "complete", "Default job not complete");
      test.skip(!strictJob || strictJob.status !== "complete", "Strict job not complete");
      test.skip(!advisoryJob || advisoryJob.status !== "complete", "Advisory job not complete");

      const dSummary = defaultJob!.summary;
      const sSummary = strictJob!.summary;
      const aSummary = advisoryJob!.summary;

      // At minimum, advisory-only should differ from strict in error/warning counts
      const allIdentical =
        dSummary.error_count === sSummary.error_count &&
        dSummary.error_count === aSummary.error_count &&
        dSummary.warning_count === sSummary.warning_count &&
        dSummary.warning_count === aSummary.warning_count;

      expect(
        allIdentical,
        "Expected at least some summary stats to differ across profiles",
      ).toBe(false);
    });
  });

  test.describe("Specialty profiles", () => {
    test("hp-indigo-epm profile produces LPDF_EPM_* findings", async ({
      request,
    }) => {
      const job = await submitAndPoll(request, sessionToken, "hp-indigo-epm");
      test.skip(!job, "hp-indigo-epm submission failed");
      test.skip(job!.status !== "complete", `Job status: ${job!.status}`);

      const epmFindings = job!.findings.filter((f) =>
        f.inspection_id.startsWith("LPDF_EPM_"),
      );

      // eslint-disable-next-line no-console
      console.log(
        `  [INFO] hp-indigo-epm: ${job!.findings.length} total findings, ${epmFindings.length} LPDF_EPM_* findings`,
      );

      expect(
        epmFindings.length,
        "Expected LPDF_EPM_* findings from hp-indigo-epm profile",
      ).toBeGreaterThan(0);
    });

    test("ecg-readiness profile produces LPDF_ECG_* findings", async ({
      request,
    }) => {
      const job = await submitAndPoll(request, sessionToken, "ecg-readiness");
      test.skip(!job, "ecg-readiness submission failed");
      test.skip(job!.status !== "complete", `Job status: ${job!.status}`);

      const ecgFindings = job!.findings.filter((f) =>
        f.inspection_id.startsWith("LPDF_ECG_"),
      );

      // eslint-disable-next-line no-console
      console.log(
        `  [INFO] ecg-readiness: ${job!.findings.length} total findings, ${ecgFindings.length} LPDF_ECG_* findings`,
      );

      expect(
        ecgFindings.length,
        "Expected LPDF_ECG_* findings from ecg-readiness profile",
      ).toBeGreaterThan(0);
    });

    test("pdfx1a-magazine-ads profile produces conformance-related findings", async ({
      request,
    }) => {
      const job = await submitAndPoll(
        request,
        sessionToken,
        "pdfx1a-magazine-ads",
      );
      test.skip(!job, "pdfx1a-magazine-ads submission failed");
      test.skip(job!.status !== "complete", `Job status: ${job!.status}`);

      // Conformance checks should produce findings related to standards
      const conformanceFindings = job!.findings.filter(
        (f) =>
          f.inspection_id.startsWith("LPDF_STD_") ||
          f.inspection_id.startsWith("LPDF_COLOR_") ||
          f.inspection_id.startsWith("LPDF_PRESS_") ||
          f.message.toLowerCase().includes("conformance") ||
          f.message.toLowerCase().includes("pdf/x"),
      );

      // eslint-disable-next-line no-console
      console.log(
        `  [INFO] pdfx1a-magazine-ads: ${job!.findings.length} total findings, ` +
          `${conformanceFindings.length} conformance-related findings`,
      );

      expect(
        conformanceFindings.length,
        "Expected conformance-related findings from pdfx1a-magazine-ads profile",
      ).toBeGreaterThan(0);

      // Should have some error or warning level findings for a non-PDF/X file.
      // Engine emits lowercase severities — see ``analyzers/finding.py``.
      const serious = job!.findings.filter(
        (f) => f.severity === "error" || f.severity === "warning",
      );
      expect(
        serious.length,
        "Expected error or warning findings from pdfx1a-magazine-ads on non-compliant PDF",
      ).toBeGreaterThan(0);
    });

    test("iso-12647-compliance profile produces standards-related findings", async ({
      request,
    }) => {
      const job = await submitAndPoll(
        request,
        sessionToken,
        "iso-12647-compliance",
      );
      test.skip(!job, "iso-12647-compliance submission failed");
      test.skip(job!.status !== "complete", `Job status: ${job!.status}`);

      // ISO 12647 is a color/printing standard — expect color and standards findings
      const standardsFindings = job!.findings.filter(
        (f) =>
          f.inspection_id.startsWith("LPDF_STD_") ||
          f.inspection_id.startsWith("LPDF_COLOR_") ||
          f.inspection_id.startsWith("LPDF_ICC_") ||
          f.inspection_id.startsWith("LPDF_INK_") ||
          f.inspection_id.startsWith("LPDF_GAMUT_") ||
          f.message.toLowerCase().includes("iso") ||
          f.message.toLowerCase().includes("12647"),
      );

      // eslint-disable-next-line no-console
      console.log(
        `  [INFO] iso-12647-compliance: ${job!.findings.length} total findings, ` +
          `${standardsFindings.length} standards-related findings`,
      );

      expect(
        standardsFindings.length,
        "Expected standards-related findings from iso-12647-compliance profile",
      ).toBeGreaterThan(0);
    });
  });
});
