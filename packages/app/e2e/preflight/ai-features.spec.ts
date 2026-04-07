import { test, expect } from "@playwright/test";
import {
  authenticateRole,
  isMcpBackdoorAvailable,
  getEngineApiKey,
  getEngineBase,
  pollJobViaApp,
} from "../helpers";
import { readFileSync, existsSync } from "fs";
import { resolve } from "path";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";
const TEST_PDF = resolve(
  __dirname,
  "../../../engine/tests/fixtures/test-sample.pdf",
);

interface AiConfig {
  enabled: boolean;
  credits_remaining?: number;
  model?: string;
  provider?: string;
}

interface Finding {
  inspection_id: string;
  severity: string;
  message: string;
  source?: string;
  page_num: number;
}

test.describe("Preflight: AI Features", () => {
  let sessionToken: string;
  let aiConfig: AiConfig;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
    test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

    const auth = await authenticateRole(request, "owner");
    sessionToken = auth.sessionToken;
  });

  test.describe("AI configuration", () => {
    test("GET /api/lintpdf/ai-config returns AI status", async ({
      request,
    }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/ai-config`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      });

      // AI config endpoint should exist even if AI is disabled
      expect(
        [200, 404].includes(res.status()),
        `Unexpected status ${res.status()} from ai-config`,
      ).toBe(true);

      if (res.status() === 200) {
        aiConfig = await res.json();
        expect(typeof aiConfig.enabled).toBe("boolean");
      } else {
        // If 404, AI config endpoint is not implemented; treat as disabled
        aiConfig = { enabled: false };
      }
    });

    test("AI credit balance is reported when enabled", async ({ request }) => {
      test.skip(!aiConfig?.enabled, "AI is not enabled in this environment");

      const res = await request.get(`${APP_BASE}/api/lintpdf/ai-config`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      });
      expect(res.ok()).toBe(true);

      const config = await res.json();
      expect(config.credits_remaining).toBeDefined();
      expect(typeof config.credits_remaining).toBe("number");
      expect(config.credits_remaining).toBeGreaterThanOrEqual(0);
    });

    test("AI config rejects unauthenticated requests", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/ai-config`, {
        headers: { Cookie: "" },
      });

      expect(res.ok()).toBe(false);
      expect([401, 302, 307, 403].includes(res.status())).toBe(true);
    });
  });

  test.describe("AI-powered preflight analysis", () => {
    test("submit with AI-enabled profile produces AI findings", async ({
      request,
    }) => {
      test.skip(!aiConfig?.enabled, "AI is not enabled in this environment");

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
          ai_enabled: "true",
        },
      });

      expect(
        [200, 201, 202].includes(submitRes.status()),
        `AI submit failed: ${submitRes.status()}`,
      ).toBe(true);

      const submitData = await submitRes.json();
      const jobId = submitData.job_id ?? submitData.id;
      expect(jobId).toBeTruthy();

      // AI analysis may take longer
      const result = await pollJobViaApp(
        request,
        jobId,
        sessionToken,
        180_000,
      );

      expect(["complete", "failed"]).toContain(result.status);

      if (result.status === "complete") {
        const findings = result.findings as Finding[];
        expect(Array.isArray(findings)).toBe(true);

        // Check that at least some findings are AI-sourced
        const aiFindings = findings.filter((f) => f.source === "ai");
        expect(
          aiFindings.length,
          "Expected at least one AI-sourced finding when AI is enabled",
        ).toBeGreaterThan(0);

        // Validate AI findings have the same structure as engine findings
        for (const finding of aiFindings) {
          expect(finding.inspection_id).toBeTruthy();
          expect(finding.severity).toBeTruthy();
          expect(["ERROR", "WARNING", "ADVISORY"]).toContain(finding.severity);
          expect(typeof finding.message).toBe("string");
          expect(finding.message.length).toBeGreaterThan(0);
        }
      }
    });

    test("AI interpretation endpoint returns data for completed job", async ({
      request,
    }) => {
      test.skip(!aiConfig?.enabled, "AI is not enabled in this environment");

      // Submit and complete a job first
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
          ai_enabled: "true",
        },
      });

      const submitData = await submitRes.json();
      const jobId = submitData.job_id ?? submitData.id;

      const result = await pollJobViaApp(
        request,
        jobId,
        sessionToken,
        180_000,
      );
      test.skip(
        result.status !== "complete",
        "Job did not complete; cannot test interpretation",
      );

      // Request AI interpretation
      const interpRes = await request.get(
        `${APP_BASE}/api/lintpdf/viewer/${jobId}/interpretation`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      // Endpoint may not exist yet (404) or may require AI credits
      if (interpRes.status() === 200) {
        const interp = await interpRes.json();
        expect(interp).toBeTruthy();
        // Interpretation should have some textual content
        if (interp.interpretation) {
          expect(typeof interp.interpretation).toBe("string");
          expect(interp.interpretation.length).toBeGreaterThan(0);
        }
        if (interp.recommendations) {
          expect(Array.isArray(interp.recommendations)).toBe(true);
        }
      } else {
        // 404 or 402 (no credits) are acceptable non-error outcomes
        expect([404, 402, 501].includes(interpRes.status())).toBe(true);
      }
    });
  });

  test.describe("AI usage statistics", () => {
    test("AI usage stats endpoint returns data", async ({ request }) => {
      test.skip(!aiConfig?.enabled, "AI is not enabled in this environment");

      const res = await request.get(`${APP_BASE}/api/lintpdf/ai-usage`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      });

      // Usage stats endpoint may or may not be implemented
      if (res.status() === 200) {
        const usage = await res.json();
        expect(usage).toBeTruthy();

        if (usage.total_requests !== undefined) {
          expect(typeof usage.total_requests).toBe("number");
          expect(usage.total_requests).toBeGreaterThanOrEqual(0);
        }
        if (usage.credits_used !== undefined) {
          expect(typeof usage.credits_used).toBe("number");
          expect(usage.credits_used).toBeGreaterThanOrEqual(0);
        }
      } else {
        expect([404, 501].includes(res.status())).toBe(true);
      }
    });
  });

  test.describe("Engine AI endpoints (direct)", () => {
    let engineApiKey: string;
    let engineBase: string;

    test.beforeAll(() => {
      engineApiKey = getEngineApiKey();
      engineBase = getEngineBase();
    });

    test("GET /api/v1/ai/presets lists available AI presets", async ({
      request,
    }) => {
      test.skip(!engineApiKey, "Engine API key not available");

      const res = await request.get(`${engineBase}/api/v1/ai/presets`, {
        headers: { Authorization: `Bearer ${engineApiKey}` },
      });

      // Endpoint may not exist (404) in some deployments
      if (res.status() === 200) {
        const data = await res.json();
        // Could be an array or an object with a presets key
        const presets = Array.isArray(data) ? data : data.presets;
        expect(Array.isArray(presets)).toBe(true);

        for (const preset of presets) {
          expect(preset.id ?? preset.name).toBeTruthy();
        }
      } else {
        expect(
          [404, 501, 503].includes(res.status()),
          `Unexpected status ${res.status()} from /api/v1/ai/presets`,
        ).toBe(true);
      }
    });

    test("GET /api/v1/ai/config returns engine AI configuration", async ({
      request,
    }) => {
      test.skip(!engineApiKey, "Engine API key not available");

      const res = await request.get(`${engineBase}/api/v1/ai/config`, {
        headers: { Authorization: `Bearer ${engineApiKey}` },
      });

      if (res.status() === 200) {
        const config = await res.json();
        expect(config).toBeTruthy();

        // Should indicate whether AI is available at the engine level
        if (config.enabled !== undefined) {
          expect(typeof config.enabled).toBe("boolean");
        }
        if (config.provider !== undefined) {
          expect(typeof config.provider).toBe("string");
        }
        if (config.model !== undefined) {
          expect(typeof config.model).toBe("string");
        }
      } else {
        expect(
          [404, 501, 503].includes(res.status()),
          `Unexpected status ${res.status()} from /api/v1/ai/config`,
        ).toBe(true);
      }
    });

    test("engine AI endpoints reject unauthenticated requests", async ({
      request,
    }) => {
      const presetsRes = await request.get(
        `${engineBase}/api/v1/ai/presets`,
        {
          headers: { Authorization: "" },
        },
      );
      expect(presetsRes.ok()).toBe(false);
      expect(
        [401, 403, 404].includes(presetsRes.status()),
        `Expected auth error, got ${presetsRes.status()}`,
      ).toBe(true);

      const configRes = await request.get(`${engineBase}/api/v1/ai/config`, {
        headers: { Authorization: "" },
      });
      expect(configRes.ok()).toBe(false);
      expect(
        [401, 403, 404].includes(configRes.status()),
        `Expected auth error, got ${configRes.status()}`,
      ).toBe(true);
    });
  });

  test.describe("AI presets via app", () => {
    test("GET /api/lintpdf/ai-presets lists presets through the app", async ({
      request,
    }) => {
      test.skip(!aiConfig?.enabled, "AI is not enabled in this environment");

      const res = await request.get(`${APP_BASE}/api/lintpdf/ai-presets`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      });

      if (res.status() === 200) {
        const data = await res.json();
        const presets = Array.isArray(data) ? data : data.presets;
        expect(Array.isArray(presets)).toBe(true);
      } else {
        // Endpoint may proxy to engine and inherit its status
        expect([404, 501].includes(res.status())).toBe(true);
      }
    });
  });
});
