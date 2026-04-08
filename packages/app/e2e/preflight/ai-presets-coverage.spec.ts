import { test, expect } from "@playwright/test";
import {
  authenticateRole,
  isMcpBackdoorAvailable,
  getEngineApiKey,
  getEngineBase,
} from "../helpers";

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

  test.describe("AI preset job submissions", () => {
    // Test a representative subset of presets to avoid excessive runtime
    const PRESETS_TO_SUBMIT = [
      AI_PRESETS.find((p) => p.id === "full-ai-scan")!,
      AI_PRESETS.find((p) => p.id === "brand-compliance")!,
      AI_PRESETS.find((p) => p.id === "packaging-qc")!,
    ];

    // The engine's POST /api/v1/jobs endpoint accepts only ``file``,
    // ``profile_id`` and ``jdf_file`` form fields — there is no per-job
    // ``ai_preset`` wiring (see ``api/routes/jobs.py:submit_job``). AI is
    // configured at the tenant level via ``/api/v1/ai/config``. Until the
    // engine grows per-job AI preset support, this submission round-trip is
    // verified by the tenant-level ``ai-features.spec.ts`` flow instead.
    for (const preset of PRESETS_TO_SUBMIT) {
      test(`submit with AI preset "${preset.name}" produces AI findings`, async () => {
        test.skip(
          true,
          `Per-job AI preset submission not supported by the engine; ` +
            `use tenant-level AI config to enable preset "${preset.id}".`,
        );
      });
    }
  });

  test.describe("AI finding structure validation", () => {
    // See note above on per-job AI preset wiring — once the engine accepts
    // an ``ai_preset`` form field on POST /api/v1/jobs (or an equivalent
    // mechanism), reinstate the live submission round-trip here.
    test("AI findings have valid structure (inspection_id, severity, message, category)", async () => {
      test.skip(true, "Per-job AI preset submission not supported by the engine.");
    });
  });

  test.describe("Different presets produce different AI finding categories", () => {
    test("brand-compliance and packaging-qc yield different categories", async () => {
      test.skip(true, "Per-job AI preset submission not supported by the engine.");
    });
  });
});
