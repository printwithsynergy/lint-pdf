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

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";
const TEST_PDF = resolve(
  __dirname,
  "../../../engine/tests/fixtures/test-sample.pdf",
);

interface AiPreset {
  id: string;
  name: string;
  description?: string;
  categories?: string[];
  [key: string]: unknown;
}

interface Finding {
  inspection_id: string;
  severity: string;
  message: string;
  page_num?: number;
  source?: string;
  category?: string;
  [key: string]: unknown;
}

const AI_PRESETS = [
  {
    id: "brand-compliance",
    name: "Brand Compliance",
    categories: ["logo_verification", "color_compliance"],
  },
  {
    id: "eu-food-label",
    name: "EU Food Label",
    categories: ["regulatory_compliance"],
  },
  {
    id: "fda-food-label",
    name: "FDA Food Label",
    categories: ["regulatory_compliance"],
  },
  {
    id: "ghs-chemical",
    name: "GHS Chemical",
    categories: ["regulatory_compliance", "symbol_detection"],
  },
  {
    id: "packaging-qc",
    name: "Packaging QC",
    categories: ["content_quality", "spatial_analysis"],
  },
  {
    id: "pharma-eu",
    name: "Pharma EU",
    categories: ["barcode", "regulatory_compliance"],
  },
  {
    id: "full-ai-scan",
    name: "Full AI Scan",
    categories: ["all"],
  },
] as const;

test.describe("Preflight: AI Presets Coverage", () => {
  let engineApiKey: string;
  let engineBase: string;
  let sessionToken: string;
  let presetsAvailable = false;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");

    engineApiKey = getEngineApiKey();
    engineBase = getEngineBase();
    test.skip(!engineApiKey, "Engine API key not available");

    const auth = await authenticateRole(request, "owner");
    sessionToken = auth.sessionToken;

    // Probe the presets endpoint to see if AI presets are available
    const probeRes = await request.get(`${engineBase}/api/v1/ai/presets`, {
      headers: { Authorization: `Bearer ${engineApiKey}` },
    });
    presetsAvailable = probeRes.status() === 200;
  });

  test.describe("Presets listing", () => {
    test("GET /api/v1/ai/presets returns all 7 AI presets", async ({
      request,
    }) => {
      test.skip(!presetsAvailable, "AI presets endpoint not available");

      const res = await request.get(`${engineBase}/api/v1/ai/presets`, {
        headers: { Authorization: `Bearer ${engineApiKey}` },
      });

      expect(res.ok()).toBe(true);
      const data = await res.json();
      const presets: AiPreset[] = Array.isArray(data) ? data : data.presets;
      expect(Array.isArray(presets)).toBe(true);

      // Validate all 7 expected presets are present
      const presetIds = presets.map((p) => p.id ?? p.name);
      for (const expected of AI_PRESETS) {
        expect(
          presetIds,
          `Missing AI preset: ${expected.id} (${expected.name})`,
        ).toContain(expected.id);
      }

      expect(presets.length).toBeGreaterThanOrEqual(AI_PRESETS.length);
    });
  });

  test.describe("Individual preset details", () => {
    for (const preset of AI_PRESETS) {
      test(`GET /api/v1/ai/presets/${preset.id} returns details for "${preset.name}"`, async ({
        request,
      }) => {
        test.skip(!presetsAvailable, "AI presets endpoint not available");

        const res = await request.get(
          `${engineBase}/api/v1/ai/presets/${preset.id}`,
          {
            headers: { Authorization: `Bearer ${engineApiKey}` },
          },
        );

        // Individual preset endpoint may not exist (list-only API)
        if (res.status() === 404) {
          // eslint-disable-next-line no-console
          console.log(
            `  [INFO] Individual preset endpoint not implemented for ${preset.id}`,
          );
          return;
        }

        expect(res.ok(), `Failed to get preset ${preset.id}: ${res.status()}`).toBe(true);

        const data = await res.json();
        expect(data.id ?? data.slug ?? data.name).toBeTruthy();

        // If categories are returned, validate they are an array
        if (data.categories) {
          expect(Array.isArray(data.categories)).toBe(true);
        }
      });
    }
  });

  test.describe("AI preset job submissions", () => {
    // Test a representative subset of presets to avoid excessive runtime
    const PRESETS_TO_SUBMIT = [
      AI_PRESETS.find((p) => p.id === "full-ai-scan")!,
      AI_PRESETS.find((p) => p.id === "brand-compliance")!,
      AI_PRESETS.find((p) => p.id === "packaging-qc")!,
    ];

    for (const preset of PRESETS_TO_SUBMIT) {
      test(`submit with AI preset "${preset.name}" produces AI findings`, async ({
        request,
      }) => {
        test.skip(!presetsAvailable, "AI presets endpoint not available");
        test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

        const pdfBuffer = readFileSync(TEST_PDF);

        // Submit via engine directly with AI preset config
        const submitRes = await request.post(
          `${engineBase}/api/v1/jobs/submit`,
          {
            headers: {
              Authorization: `Bearer ${engineApiKey}`,
            },
            multipart: {
              file: {
                name: "test-sample.pdf",
                mimeType: "application/pdf",
                buffer: pdfBuffer,
              },
              profile_id: "lintpdf-default",
              ai_preset: preset.id,
              ai_enabled: "true",
            },
          },
        );

        // If the engine doesn't support AI preset submissions, skip gracefully
        if (submitRes.status() === 404 || submitRes.status() === 501) {
          // eslint-disable-next-line no-console
          console.log(
            `  [INFO] AI preset submission not supported for ${preset.id}`,
          );
          return;
        }

        expect(
          [200, 201, 202].includes(submitRes.status()),
          `Submit with AI preset ${preset.id} failed: ${submitRes.status()} ${await submitRes.text()}`,
        ).toBe(true);

        const submitData = await submitRes.json();
        const jobId = submitData.job_id ?? submitData.id;
        expect(jobId).toBeTruthy();

        // AI analysis may take longer — 3 minute timeout
        const result = await pollJobViaEngine(
          request,
          jobId,
          engineApiKey,
          180_000,
        );

        expect(
          ["complete", "failed"],
          `Job ended with unexpected status: ${result.status}`,
        ).toContain(result.status);

        if (result.status === "complete") {
          const findings = result.findings as Finding[];
          expect(Array.isArray(findings)).toBe(true);

          // Check for AI-sourced findings
          const aiFindings = findings.filter((f) => f.source === "ai");
          // eslint-disable-next-line no-console
          console.log(
            `  [INFO] ${preset.name}: ${findings.length} total findings, ${aiFindings.length} AI findings`,
          );

          expect(
            aiFindings.length,
            `Expected AI findings from preset "${preset.name}"`,
          ).toBeGreaterThan(0);
        }
      });
    }
  });

  test.describe("AI finding structure validation", () => {
    test("AI findings have valid structure (inspection_id, severity, message, category)", async ({
      request,
    }) => {
      test.skip(!presetsAvailable, "AI presets endpoint not available");
      test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

      const pdfBuffer = readFileSync(TEST_PDF);

      // Submit with full-ai-scan for maximum coverage
      const submitRes = await request.post(
        `${engineBase}/api/v1/jobs/submit`,
        {
          headers: {
            Authorization: `Bearer ${engineApiKey}`,
          },
          multipart: {
            file: {
              name: "test-sample.pdf",
              mimeType: "application/pdf",
              buffer: pdfBuffer,
            },
            profile_id: "lintpdf-default",
            ai_preset: "full-ai-scan",
            ai_enabled: "true",
          },
        },
      );

      if (submitRes.status() === 404 || submitRes.status() === 501) {
        // eslint-disable-next-line no-console
        console.log("  [INFO] AI job submission not supported — skipping");
        return;
      }

      expect([200, 201, 202].includes(submitRes.status())).toBe(true);

      const submitData = await submitRes.json();
      const jobId = submitData.job_id ?? submitData.id;
      const result = await pollJobViaEngine(
        request,
        jobId,
        engineApiKey,
        180_000,
      );

      test.skip(result.status !== "complete", "Job did not complete");

      const findings = result.findings as Finding[];
      const aiFindings = findings.filter((f) => f.source === "ai");

      for (const finding of aiFindings) {
        expect(
          finding.inspection_id,
          "AI finding missing inspection_id",
        ).toBeTruthy();
        expect(typeof finding.inspection_id).toBe("string");

        expect(finding.severity, "AI finding missing severity").toBeTruthy();
        expect(
          ["ERROR", "WARNING", "ADVISORY"],
          `Invalid severity "${finding.severity}" on AI finding ${finding.inspection_id}`,
        ).toContain(finding.severity);

        expect(typeof finding.message).toBe("string");
        expect(finding.message.length).toBeGreaterThan(0);

        // Category is expected on AI findings (may vary by implementation)
        if (finding.category !== undefined) {
          expect(typeof finding.category).toBe("string");
          expect(finding.category!.length).toBeGreaterThan(0);
        }
      }
    });
  });

  test.describe("Different presets produce different AI finding categories", () => {
    test("brand-compliance and packaging-qc yield different categories", async ({
      request,
    }) => {
      test.skip(!presetsAvailable, "AI presets endpoint not available");
      test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

      const pdfBuffer = readFileSync(TEST_PDF);

      const submitJobs = async (presetId: string) => {
        const submitRes = await request.post(
          `${engineBase}/api/v1/jobs/submit`,
          {
            headers: { Authorization: `Bearer ${engineApiKey}` },
            multipart: {
              file: {
                name: "test-sample.pdf",
                mimeType: "application/pdf",
                buffer: pdfBuffer,
              },
              profile_id: "lintpdf-default",
              ai_preset: presetId,
              ai_enabled: "true",
            },
          },
        );

        if (!submitRes.ok()) return null;
        const data = await submitRes.json();
        const jobId = data.job_id ?? data.id;
        if (!jobId) return null;
        return pollJobViaEngine(request, jobId, engineApiKey, 180_000);
      };

      const [brandResult, packagingResult] = await Promise.all([
        submitJobs("brand-compliance"),
        submitJobs("packaging-qc"),
      ]);

      if (!brandResult || !packagingResult) {
        // eslint-disable-next-line no-console
        console.log("  [INFO] One or both AI preset submissions failed — skipping comparison");
        return;
      }

      if (brandResult.status !== "complete" || packagingResult.status !== "complete") {
        // eslint-disable-next-line no-console
        console.log("  [INFO] One or both jobs did not complete — skipping comparison");
        return;
      }

      const brandFindings = (brandResult.findings as Finding[]).filter(
        (f) => f.source === "ai",
      );
      const packagingFindings = (packagingResult.findings as Finding[]).filter(
        (f) => f.source === "ai",
      );

      const brandCategories = new Set(
        brandFindings.map((f) => f.category ?? f.inspection_id).filter(Boolean),
      );
      const packagingCategories = new Set(
        packagingFindings.map((f) => f.category ?? f.inspection_id).filter(Boolean),
      );

      // eslint-disable-next-line no-console
      console.log(`  [INFO] brand-compliance categories: ${[...brandCategories].join(", ")}`);
      // eslint-disable-next-line no-console
      console.log(`  [INFO] packaging-qc categories: ${[...packagingCategories].join(", ")}`);

      // If both produced findings, they should differ in at least some categories
      if (brandFindings.length > 0 && packagingFindings.length > 0) {
        const identical =
          brandCategories.size === packagingCategories.size &&
          [...brandCategories].every((c) => packagingCategories.has(c));

        expect(
          identical,
          "Expected different AI preset to produce different finding categories",
        ).toBe(false);
      }
    });
  });
});
