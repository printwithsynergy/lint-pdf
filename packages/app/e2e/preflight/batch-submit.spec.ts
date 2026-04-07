import { test, expect } from "@playwright/test";
import {
  authenticateRole,
  isMcpBackdoorAvailable,
  getEngineApiKey,
  getEngineBase,
} from "../helpers";
import { readFileSync, existsSync } from "fs";
import { resolve } from "path";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";
const TEST_PDF = resolve(
  __dirname,
  "../../../engine/tests/fixtures/test-sample.pdf",
);

interface BatchStatus {
  batch_id?: string;
  id?: string;
  status: string;
  jobs?: Array<{
    job_id?: string;
    id?: string;
    status: string;
    filename?: string;
    [key: string]: unknown;
  }>;
  total?: number;
  completed?: number;
  failed?: number;
  [key: string]: unknown;
}

/** Poll a batch until all jobs reach a terminal state. */
async function pollBatch(
  request: import("@playwright/test").APIRequestContext,
  batchId: string,
  engineBase: string,
  apiKey: string,
  maxWaitMs = 180_000,
  intervalMs = 3_000,
): Promise<BatchStatus> {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    const res = await request.get(
      `${engineBase}/api/v1/batch/${batchId}`,
      {
        headers: { Authorization: `Bearer ${apiKey}` },
      },
    );
    if (res.ok()) {
      const data = (await res.json()) as BatchStatus;
      if (
        data.status === "complete" ||
        data.status === "completed" ||
        data.status === "failed" ||
        data.status === "partial"
      ) {
        return data;
      }
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`Batch ${batchId} did not complete within ${maxWaitMs}ms`);
}

test.describe("Preflight: Batch Submit", () => {
  let engineApiKey: string;
  let engineBase: string;
  let sessionToken: string;
  let batchEndpointAvailable = false;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
    test.skip(!existsSync(TEST_PDF), `Test PDF not found at ${TEST_PDF}`);

    engineApiKey = getEngineApiKey();
    engineBase = getEngineBase();
    test.skip(!engineApiKey, "Engine API key not available");

    const auth = await authenticateRole(request, "owner");
    sessionToken = auth.sessionToken;

    // Probe batch endpoint availability
    const probeRes = await request.get(`${engineBase}/api/v1/batch/nonexistent`, {
      headers: { Authorization: `Bearer ${engineApiKey}` },
    });
    // 404 on a specific batch ID means the endpoint exists;
    // 404 could also mean the route doesn't exist. Distinguish via the response body.
    batchEndpointAvailable =
      probeRes.status() !== 404 ||
      (await probeRes.text()).toLowerCase().includes("batch") ||
      (await probeRes.text()).toLowerCase().includes("not found");
  });

  test.describe("Batch submission and polling", () => {
    let batchResult: BatchStatus | null = null;
    let batchId: string;

    test("POST to batch endpoint with 2 files creates a batch", async ({
      request,
    }) => {
      test.skip(!batchEndpointAvailable, "Batch endpoint not available");

      const pdfBuffer = readFileSync(TEST_PDF);

      const submitRes = await request.post(
        `${engineBase}/api/v1/batch/submit`,
        {
          headers: { Authorization: `Bearer ${engineApiKey}` },
          multipart: {
            "files[0]": {
              name: "test-sample-1.pdf",
              mimeType: "application/pdf",
              buffer: pdfBuffer,
            },
            "files[1]": {
              name: "test-sample-2.pdf",
              mimeType: "application/pdf",
              buffer: pdfBuffer,
            },
            profile_id: "lintpdf-default",
          },
        },
      );

      if (submitRes.status() === 404 || submitRes.status() === 501) {
        batchEndpointAvailable = false;
        test.skip(true, "Batch submit endpoint not implemented");
        return;
      }

      expect(
        [200, 201, 202].includes(submitRes.status()),
        `Batch submit failed: ${submitRes.status()} ${await submitRes.text()}`,
      ).toBe(true);

      const data = await submitRes.json();
      batchId = data.batch_id ?? data.id;
      expect(batchId, "No batch ID returned").toBeTruthy();
    });

    test("poll batch status until complete", async ({ request }) => {
      test.skip(!batchEndpointAvailable, "Batch endpoint not available");
      test.skip(!batchId, "No batch ID from previous test");

      batchResult = await pollBatch(
        request,
        batchId,
        engineBase,
        engineApiKey,
      );

      expect(
        ["complete", "completed", "partial"],
        `Batch ended with unexpected status: ${batchResult.status}`,
      ).toContain(batchResult.status);
    });

    test("batch summary has results for each file", () => {
      test.skip(!batchResult, "No batch result available");

      const jobs = batchResult!.jobs;
      expect(
        Array.isArray(jobs),
        "Batch result missing jobs array",
      ).toBe(true);

      // We submitted 2 files
      expect(
        jobs!.length,
        `Expected 2 jobs in batch, got ${jobs!.length}`,
      ).toBe(2);

      for (const job of jobs!) {
        const jobId = job.job_id ?? job.id;
        expect(jobId, "Batch job missing ID").toBeTruthy();
        expect(
          ["complete", "completed", "failed"],
          `Batch job ${jobId} has unexpected status: ${job.status}`,
        ).toContain(job.status);
      }
    });

    test("individual job results are accessible from batch", async ({
      request,
    }) => {
      test.skip(!batchResult, "No batch result available");

      const jobs = batchResult!.jobs;
      test.skip(!jobs || jobs.length === 0, "No jobs in batch result");

      for (const job of jobs!) {
        const jobId = job.job_id ?? job.id;
        if (!jobId) continue;

        const res = await request.get(
          `${engineBase}/api/v1/jobs/${jobId}`,
          {
            headers: { Authorization: `Bearer ${engineApiKey}` },
          },
        );

        expect(
          res.ok(),
          `Failed to get job ${jobId}: ${res.status()}`,
        ).toBe(true);

        const jobData = await res.json();
        expect(jobData.status).toBeTruthy();

        if (jobData.status === "complete") {
          expect(jobData.findings).toBeDefined();
          expect(jobData.summary).toBeDefined();
        }
      }
    });
  });

  test.describe("Batch auth and validation", () => {
    test("batch submit rejects unauthenticated requests", async ({
      request,
    }) => {
      test.skip(!batchEndpointAvailable, "Batch endpoint not available");

      const pdfBuffer = readFileSync(TEST_PDF);

      const res = await request.post(`${engineBase}/api/v1/batch/submit`, {
        headers: { Authorization: "" },
        multipart: {
          "files[0]": {
            name: "test-sample.pdf",
            mimeType: "application/pdf",
            buffer: pdfBuffer,
          },
          profile_id: "lintpdf-default",
        },
      });

      expect(res.ok()).toBe(false);
      expect(
        [401, 403].includes(res.status()),
        `Expected 401/403, got ${res.status()}`,
      ).toBe(true);
    });

    test("batch submit rejects invalid files", async ({ request }) => {
      test.skip(!batchEndpointAvailable, "Batch endpoint not available");

      const invalidBuffer = Buffer.from("this is not a PDF file");

      const res = await request.post(`${engineBase}/api/v1/batch/submit`, {
        headers: { Authorization: `Bearer ${engineApiKey}` },
        multipart: {
          "files[0]": {
            name: "not-a-pdf.pdf",
            mimeType: "application/pdf",
            buffer: invalidBuffer,
          },
          profile_id: "lintpdf-default",
        },
      });

      // Server may reject immediately (400/422) or accept and mark job as failed
      if (res.ok()) {
        const data = await res.json();
        const bId = data.batch_id ?? data.id;
        if (bId) {
          // If accepted, the batch should eventually fail or have failed jobs
          const result = await pollBatch(
            request,
            bId,
            engineBase,
            engineApiKey,
            60_000,
          );
          const failedJobs = result.jobs?.filter(
            (j) => j.status === "failed",
          );
          expect(
            failedJobs?.length,
            "Expected invalid PDF to produce a failed job",
          ).toBeGreaterThan(0);
        }
      } else {
        expect(
          [400, 415, 422].includes(res.status()),
          `Expected validation error, got ${res.status()}`,
        ).toBe(true);
      }
    });
  });
});
