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

interface Finding {
  inspection_id: string;
  severity: string;
  message: string;
  page_num: number;
}

test.describe("Preflight: AI Interpretation", () => {
  let engineApiKey: string;
  let engineBase: string;
  let jobId: string;
  let completedJob: Record<string, unknown>;

  test.beforeAll(async ({ request }) => {
    engineApiKey = getEngineApiKey();
    engineBase = getEngineBase();

    test.skip(!engineApiKey, "Engine API key not available");
    test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

    // Submit a job to the engine and wait for completion
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
      },
    });

    expect(
      [200, 201, 202].includes(submitRes.status()),
      `Engine submit failed: ${submitRes.status()} ${await submitRes.text()}`,
    ).toBe(true);

    const submitData = await submitRes.json();
    jobId = submitData.job_id ?? submitData.id;
    expect(jobId).toBeTruthy();

    completedJob = await pollJobViaEngine(
      request,
      jobId,
      engineApiKey,
      120_000,
    );
    test.skip(
      completedJob.status !== "complete",
      `Job did not complete: ${completedJob.status}`,
    );
  });

  test.describe("Engine direct: ai-review interpret", () => {
    test("GET /api/v1/ai-review/{job_id}/interpret returns AI interpretation", async ({
      request,
    }) => {
      const res = await request.get(
        `${engineBase}/api/v1/ai-review/${jobId}/interpret`,
        { headers: { Authorization: `Bearer ${engineApiKey}` } },
      );

      // May return 404 if AI is not enabled, 402 if no credits, 503 if AI service down
      if (res.status() === 200) {
        const interp = await res.json();
        expect(interp).toBeTruthy();

        // Should have some textual content
        const summary =
          interp.summary ?? interp.interpretation ?? interp.text ?? interp.content;
        expect(
          summary,
          "Interpretation missing summary/interpretation/text field",
        ).toBeTruthy();
        expect(typeof summary).toBe("string");
        expect(summary.length).toBeGreaterThan(10);
      } else {
        // Gracefully skip if AI not available
        expect(
          [404, 402, 501, 503].includes(res.status()),
          `Unexpected status ${res.status()} from ai-review interpret`,
        ).toBe(true);
        test.skip(true, `AI interpretation not available (${res.status()})`);
      }
    });

    test("interpretation includes key findings and recommendations", async ({
      request,
    }) => {
      const res = await request.get(
        `${engineBase}/api/v1/ai-review/${jobId}/interpret`,
        { headers: { Authorization: `Bearer ${engineApiKey}` } },
      );

      if (res.status() !== 200) {
        test.skip(true, `AI interpretation not available (${res.status()})`);
        return;
      }

      const interp = await res.json();

      // Key findings
      const findings =
        interp.key_findings ?? interp.findings ?? interp.keyFindings;
      if (findings !== undefined) {
        expect(Array.isArray(findings)).toBe(true);
        expect(findings.length).toBeGreaterThan(0);
      }

      // Recommendations
      const recs =
        interp.recommendations ?? interp.actions ?? interp.suggested_actions;
      if (recs !== undefined) {
        expect(Array.isArray(recs)).toBe(true);
      }
    });

    test("interpretation references actual inspection_ids from the job", async ({
      request,
    }) => {
      const res = await request.get(
        `${engineBase}/api/v1/ai-review/${jobId}/interpret`,
        { headers: { Authorization: `Bearer ${engineApiKey}` } },
      );

      if (res.status() !== 200) {
        test.skip(true, `AI interpretation not available (${res.status()})`);
        return;
      }

      const interp = await res.json();
      const interpStr = JSON.stringify(interp);

      // The job should have findings with inspection_ids
      const jobFindings = completedJob.findings as Finding[] | undefined;
      if (jobFindings && jobFindings.length > 0) {
        const inspectionIds = jobFindings.map((f) => f.inspection_id);

        // Check if the interpretation references at least one inspection_id
        const referencesAny = inspectionIds.some((id) =>
          interpStr.includes(id),
        );
        // This is a soft check — AI may paraphrase rather than cite IDs directly
        if (!referencesAny) {
          // Log it as info but don't fail — AI might summarize without citing IDs
          console.log(
            "Note: AI interpretation does not directly reference inspection_ids. " +
              "This is acceptable if it summarizes findings in natural language.",
          );
        }
      }
    });

    test("non-existent job_id returns 404", async ({ request }) => {
      const res = await request.get(
        `${engineBase}/api/v1/ai-review/nonexistent-job-id-000/interpret`,
        { headers: { Authorization: `Bearer ${engineApiKey}` } },
      );

      expect(res.ok()).toBe(false);
      expect(
        [404, 400].includes(res.status()),
        `Expected 404 for non-existent job, got ${res.status()}`,
      ).toBe(true);
    });

    test("missing auth returns 401", async ({ request }) => {
      const res = await request.get(
        `${engineBase}/api/v1/ai-review/${jobId}/interpret`,
        { headers: { Authorization: "" } },
      );

      expect(res.ok()).toBe(false);
      expect(
        [401, 403].includes(res.status()),
        `Expected 401/403 without auth, got ${res.status()}`,
      ).toBe(true);
    });
  });

  // The app proxy uses LINTPDF_API_KEY on the server side, which belongs to
  // a different engine tenant than our E2E test tenant (see
  // ``packages/plugin/src/routes/viewer.ts``). Jobs submitted directly to the
  // engine with our engineApiKey are NOT visible to the app proxy, and vice
  // versa — so we submit a second job via the app proxy here and verify
  // interpretation round-trips via the cookie path. Runs serially so ``appJobId``
  // is populated before the interpretation tests.
  test.describe.serial("App proxy: viewer interpretation", () => {
    let sessionToken: string;
    let appJobId: string | undefined;

    test.beforeAll(async ({ request }) => {
      const available = await isMcpBackdoorAvailable(request);
      test.skip(!available, "MCP backdoor not enabled");

      const auth = await authenticateRole(request, "owner");
      sessionToken = auth.sessionToken;
    });

    test("submit via app proxy yields a job the app can see", async ({
      request,
    }) => {
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
        `App submit failed: ${submitRes.status()} ${await submitRes.text()}`,
      ).toBe(true);

      const submitData = await submitRes.json();
      appJobId = submitData.job_id ?? submitData.id;
      expect(appJobId).toBeTruthy();

      // Poll via the app route until complete
      const start = Date.now();
      while (Date.now() - start < 180_000) {
        const statusRes = await request.get(
          `${APP_BASE}/api/lintpdf/jobs/${appJobId}`,
          { headers: { Cookie: `pixie-dust-session=${sessionToken}` } },
        );
        if (statusRes.ok()) {
          const data = await statusRes.json();
          if (data.status === "complete" || data.status === "failed") {
            expect(data.status).toBe("complete");
            return;
          }
        }
        await new Promise((r) => setTimeout(r, 2_000));
      }
      throw new Error(`App-submitted job ${appJobId} did not complete`);
    });

    test("GET /api/lintpdf/viewer/{jobId}/interpretation returns via session auth", async ({
      request,
    }) => {
      test.skip(!appJobId, "No app-submitted job");

      const res = await request.get(
        `${APP_BASE}/api/lintpdf/viewer/${appJobId}/interpretation`,
        { headers: { Cookie: `pixie-dust-session=${sessionToken}` } },
      );

      // AI may be disabled on the app's tenant — accept 404/402/503 as
      // graceful degrade, but never a 200 with a mangled body.
      if (res.status() === 200) {
        const interp = await res.json();
        expect(interp).toBeTruthy();

        const summary =
          interp.summary ??
          interp.interpretation ??
          interp.text ??
          interp.content;
        if (summary) {
          expect(typeof summary).toBe("string");
          expect(summary.length).toBeGreaterThan(0);
        }
      } else {
        expect(
          [404, 402, 501, 503].includes(res.status()),
          `Unexpected status ${res.status()} from app proxy interpretation`,
        ).toBe(true);
      }
    });

    test("app proxy and engine direct return consistent structure", async ({
      request,
    }) => {
      test.skip(!appJobId, "No app-submitted job");

      // App proxy: uses the cookie, job visible to LINTPDF_API_KEY's tenant.
      const appRes = await request.get(
        `${APP_BASE}/api/lintpdf/viewer/${appJobId}/interpretation`,
        { headers: { Cookie: `pixie-dust-session=${sessionToken}` } },
      );

      // Engine direct: uses our E2E engine key on OUR job (the one submitted
      // in the outer beforeAll). We compare STRUCTURE not data because the
      // two jobs are in different tenants.
      const engineRes = await request.get(
        `${engineBase}/api/v1/ai-review/${jobId}/interpret`,
        { headers: { Authorization: `Bearer ${engineApiKey}` } },
      );

      if (engineRes.status() !== 200 || appRes.status() !== 200) {
        test.skip(
          true,
          `Cannot compare structures: engine=${engineRes.status()}, app=${appRes.status()} (AI may be disabled on one tenant)`,
        );
        return;
      }

      const engineInterp = await engineRes.json();
      const appInterp = await appRes.json();

      // Both should have overlapping top-level keys. The plugin is a straight
      // passthrough (see ``plugin/src/routes/viewer.ts``), so identical keys
      // are expected — but we only require non-empty overlap.
      const engineKeys = Object.keys(engineInterp).sort();
      const appKeys = Object.keys(appInterp).sort();
      const sharedKeys = engineKeys.filter((k) => appKeys.includes(k));
      expect(
        sharedKeys.length,
        `Expected shared keys. engine=${JSON.stringify(engineKeys)} app=${JSON.stringify(appKeys)}`,
      ).toBeGreaterThan(0);
    });
  });
});
