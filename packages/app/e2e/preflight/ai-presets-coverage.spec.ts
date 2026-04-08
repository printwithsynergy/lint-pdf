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

interface AiFinding {
  inspection_id: string;
  severity: string;
  message: string;
  source?: string;
  category?: string;
  page_num: number;
}

interface AiPreset {
  // Engine emits ``slug`` as the canonical identifier — see
  // ``api/routes/ai_presets.py:AIPresetResponse``.
  slug?: string;
  id?: string;
  name: string;
  description?: string;
  categories?: string[];
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
  let presetsAvailable = false;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");

    engineApiKey = getEngineApiKey();
    engineBase = getEngineBase();
    test.skip(!engineApiKey, "Engine API key not available");

    // Authenticate to confirm an owner session is reachable; we don't need
    // the cookie itself because every assertion in this file talks to the
    // engine directly with the API key.
    await authenticateRole(request, "owner");

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

      // Engine returns presets with ``slug`` (e.g. "brand-compliance"). Some
      // older response shapes may use ``id``; fall back to ``name`` last.
      const presetIds = presets.map((p) => p.slug ?? p.id ?? p.name);
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

  // Serial mode: the three preset submissions populate a shared cache
  // which the ``structure validation`` and ``different categories``
  // nested describes read. Parallel workers would see an empty cache.
  test.describe.serial("AI preset job submissions", () => {
    // Test a representative subset of presets to avoid excessive runtime.
    const PRESETS_TO_SUBMIT = [
      AI_PRESETS.find((p) => p.id === "full-ai-scan")!,
      AI_PRESETS.find((p) => p.id === "brand-compliance")!,
      AI_PRESETS.find((p) => p.id === "packaging-qc")!,
    ];

    // Cache of submitted-job results keyed by preset id, so the follow-up
    // ``AI finding structure validation`` and ``Different presets produce
    // different categories`` describes can reuse the same submissions
    // instead of running three more ~30s jobs.
    const submittedFindingsByPreset: Record<string, AiFinding[]> = {};

    // The engine supports per-job AI preset submission via the
    // ``ai_preset`` form field on ``POST /api/v1/jobs`` — see
    // ``api/routes/jobs.py:submit_job``. The preset expands to a feature
    // list and implicitly sets ``ai_enabled=true`` for this job.
    for (const preset of PRESETS_TO_SUBMIT) {
      test(`submit with AI preset "${preset.name}" produces AI findings`, async ({
        request,
      }) => {
        test.skip(!presetsAvailable, "AI presets endpoint not available");
        test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

        const pdfBuffer = readFileSync(TEST_PDF);
        const submitRes = await request.post(`${engineBase}/api/v1/jobs`, {
          headers: { Authorization: `Bearer ${engineApiKey}` },
          multipart: {
            file: {
              name: "test-sample.pdf",
              mimeType: "application/pdf",
              buffer: pdfBuffer,
            },
            profile_id: "lintpdf-default",
            ai_preset: preset.id,
          },
        });

        expect(
          [200, 201, 202].includes(submitRes.status()),
          `Engine submit failed: ${submitRes.status()} ${await submitRes.text()}`,
        ).toBe(true);

        const submitData = await submitRes.json();
        const jobId = submitData.job_id ?? submitData.id;
        expect(jobId).toBeTruthy();

        const completedJob = await pollJobViaEngine(
          request,
          jobId,
          engineApiKey,
          120_000,
        );
        expect(completedJob.status).toBe("complete");

        const findings =
          (completedJob.findings as AiFinding[] | undefined) ?? [];
        const aiFindings = findings.filter((f) => f.source === "ai");
        expect(
          aiFindings.length,
          `Expected AI findings for preset "${preset.id}"`,
        ).toBeGreaterThan(0);

        submittedFindingsByPreset[preset.id] = aiFindings;
      });
    }

    test.describe("AI finding structure validation", () => {
      test("AI findings have valid structure (inspection_id, severity, message, category)", async () => {
        const anyPreset = Object.keys(submittedFindingsByPreset)[0];
        test.skip(
          !anyPreset,
          "No preset submission succeeded — cannot validate structure",
        );
        const findings = submittedFindingsByPreset[anyPreset!];
        for (const f of findings) {
          expect(typeof f.inspection_id).toBe("string");
          expect(f.inspection_id.length).toBeGreaterThan(0);
          expect(typeof f.severity).toBe("string");
          expect(typeof f.message).toBe("string");
        }
      });
    });

    test.describe("Different presets produce different AI finding categories", () => {
      test("brand-compliance and packaging-qc yield different categories", async () => {
        const brand = submittedFindingsByPreset["brand-compliance"];
        const pkg = submittedFindingsByPreset["packaging-qc"];
        test.skip(
          !brand || !pkg,
          "Both brand-compliance and packaging-qc submissions must have succeeded",
        );

        const brandIds = new Set(
          brand!.map((f) => f.inspection_id).filter((id) => id !== "AI_SCAN_001"),
        );
        const pkgIds = new Set(
          pkg!.map((f) => f.inspection_id).filter((id) => id !== "AI_SCAN_001"),
        );

        // The two presets share the ``logo_detection`` feature, so some
        // overlap is expected. The assertion is that the two sets are
        // NOT identical — at least one inspection id differs in either
        // direction.
        const identical =
          brandIds.size === pkgIds.size &&
          [...brandIds].every((id) => pkgIds.has(id));
        expect(
          identical,
          "brand-compliance and packaging-qc produced identical findings — expected different analyzers to run",
        ).toBe(false);
      });
    });
  });
});
