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
  details?: Record<string, unknown>;
  bbox?: number[];
}

// "required" means the analyzer category MUST produce at least one finding
// on the standard test PDF. Image/font findings are negative checks that only
// fire when something is wrong, so a clean fixture won't trigger them — those
// categories must stay optional even though the analyzers exist and run.
const ANALYZER_CATEGORIES = [
  { prefix: "LPDF_DOC_", name: "Document", required: true },
  { prefix: "LPDF_IMG_", name: "Image", required: false },
  { prefix: "LPDF_COLOR_", name: "Color", required: true },
  { prefix: "LPDF_FONT_", name: "Font", required: false },
  { prefix: "LPDF_BOX_", name: "Page Geometry", required: true },
  { prefix: "LPDF_TRANS_", name: "Transparency", required: false },
  { prefix: "LPDF_META_", name: "Metadata", required: true },
  { prefix: "LPDF_ANNOT_", name: "Annotations", required: false },
  { prefix: "LPDF_STRUCT_", name: "Structure", required: false },
  { prefix: "LPDF_ACCESS_", name: "Accessibility", required: false },
  { prefix: "LPDF_PATH_", name: "Hairline Paths", required: false },
  { prefix: "LPDF_STROKE_", name: "Strokes", required: false },
  { prefix: "LPDF_TEXT_", name: "Small Text", required: false },
  { prefix: "LPDF_OVER_", name: "Overprint", required: false },
  { prefix: "LPDF_BARCODE_", name: "Barcode", required: false },
  { prefix: "LPDF_ICC_", name: "ICC Profiles", required: false },
  { prefix: "LPDF_SPOT_", name: "Spot Colors", required: false },
  { prefix: "LPDF_INK_", name: "Ink Coverage", required: false },
  { prefix: "LPDF_GAMUT_", name: "Gamut", required: false },
  { prefix: "LPDF_ADV_", name: "Advanced Color", required: false },
  { prefix: "LPDF_PRESS_", name: "Prepress", required: false },
  { prefix: "LPDF_PROC_", name: "Processing", required: false },
  { prefix: "LPDF_STD_", name: "Standards", required: false },
  { prefix: "LPDF_EPM_", name: "HP Indigo EPM", required: false },
  { prefix: "LPDF_ECG_", name: "Extended Gamut", required: false },
  { prefix: "LPDF_PKG_", name: "Packaging", required: false },
] as const;

/** All known LPDF_ prefixes for validation */
const KNOWN_PREFIXES = ANALYZER_CATEGORIES.map((c) => c.prefix);

test.describe("Preflight: Analyzer Coverage", () => {
  let sessionToken: string;
  let completedJob: Record<string, unknown>;
  let findings: Finding[];

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
    test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

    const auth = await authenticateRole(request, "owner");
    sessionToken = auth.sessionToken;

    // Submit a job with the default profile (enables all LPDF_* checks)
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
    test.skip(
      completedJob.status !== "complete",
      `Job did not complete successfully: ${completedJob.status}`,
    );

    findings = completedJob.findings as Finding[];
    expect(Array.isArray(findings)).toBe(true);
    expect(findings.length).toBeGreaterThan(0);
  });

  test.describe("Required analyzer categories", () => {
    for (const category of ANALYZER_CATEGORIES.filter((c) => c.required)) {
      test(`"${category.name}" analyzer (${category.prefix}*) produces at least one finding`, () => {
        const matching = findings.filter((f) =>
          f.inspection_id.startsWith(category.prefix),
        );
        expect(
          matching.length,
          `Expected at least one finding with prefix ${category.prefix} (${category.name})`,
        ).toBeGreaterThan(0);
      });
    }
  });

  test.describe("Optional analyzer categories (informational)", () => {
    for (const category of ANALYZER_CATEGORIES.filter((c) => !c.required)) {
      test(`"${category.name}" analyzer (${category.prefix}*) — check presence (non-blocking)`, () => {
        const matching = findings.filter((f) =>
          f.inspection_id.startsWith(category.prefix),
        );
        if (matching.length > 0) {
          // Log for visibility; this is informational, not a hard assertion
          // eslint-disable-next-line no-console
          console.log(
            `  [INFO] ${category.name} (${category.prefix}*): ${matching.length} finding(s) found`,
          );
        } else {
          // eslint-disable-next-line no-console
          console.log(
            `  [INFO] ${category.name} (${category.prefix}*): no findings (OK — optional)`,
          );
        }
        // Always passes; this test is for observability
        expect(true).toBe(true);
      });
    }
  });

  test("all findings have valid LPDF_* prefixes (no unknown prefixes)", () => {
    const unknownFindings = findings.filter((f) => {
      if (!f.inspection_id.startsWith("LPDF_")) return true;
      return !KNOWN_PREFIXES.some((prefix) =>
        f.inspection_id.startsWith(prefix),
      );
    });

    if (unknownFindings.length > 0) {
      const unknownIds = [
        ...new Set(unknownFindings.map((f) => f.inspection_id)),
      ];
      // eslint-disable-next-line no-console
      console.log(`  [WARN] Unknown inspection_id prefixes: ${unknownIds.join(", ")}`);
    }

    // Every finding must at least start with LPDF_
    for (const finding of findings) {
      expect(
        finding.inspection_id,
        `Finding has invalid inspection_id: ${finding.inspection_id}`,
      ).toMatch(/^LPDF_/);
    }
  });

  test("at least 10 unique inspection_ids are found", () => {
    const uniqueIds = new Set(findings.map((f) => f.inspection_id));
    expect(
      uniqueIds.size,
      `Expected > 10 unique inspection_ids, got ${uniqueIds.size}: ${[...uniqueIds].join(", ")}`,
    ).toBeGreaterThan(10);
  });

  test("each finding has required fields: inspection_id, severity, message, page_num", () => {
    for (const finding of findings) {
      expect(
        finding.inspection_id,
        "Finding missing inspection_id",
      ).toBeTruthy();
      expect(
        typeof finding.inspection_id,
        `inspection_id is not a string: ${typeof finding.inspection_id}`,
      ).toBe("string");

      expect(finding.severity, "Finding missing severity").toBeTruthy();
      // Engine emits lowercase severities — see ``analyzers/finding.py``.
      expect(
        ["error", "warning", "advisory"],
        `Invalid severity "${finding.severity}" on ${finding.inspection_id}`,
      ).toContain(finding.severity);

      expect(
        typeof finding.message,
        `message is not a string on ${finding.inspection_id}`,
      ).toBe("string");
      expect(
        finding.message.length,
        `Empty message on ${finding.inspection_id}`,
      ).toBeGreaterThan(0);

      expect(
        typeof finding.page_num,
        `page_num is not a number on ${finding.inspection_id}`,
      ).toBe("number");
      expect(finding.page_num).toBeGreaterThanOrEqual(0);
    }
  });

  test("logs summary of categories found", () => {
    const categoryCounts: Record<string, number> = {};
    for (const category of ANALYZER_CATEGORIES) {
      const count = findings.filter((f) =>
        f.inspection_id.startsWith(category.prefix),
      ).length;
      if (count > 0) {
        categoryCounts[category.name] = count;
      }
    }

    const foundCount = Object.keys(categoryCounts).length;
    // eslint-disable-next-line no-console
    console.log(
      `  [SUMMARY] ${foundCount}/${ANALYZER_CATEGORIES.length} categories produced findings:`,
    );
    for (const [name, count] of Object.entries(categoryCounts)) {
      // eslint-disable-next-line no-console
      console.log(`    - ${name}: ${count} finding(s)`);
    }

    // At least the required categories should be present
    const requiredCount = ANALYZER_CATEGORIES.filter((c) => c.required).length;
    expect(foundCount).toBeGreaterThanOrEqual(requiredCount);
  });
});
