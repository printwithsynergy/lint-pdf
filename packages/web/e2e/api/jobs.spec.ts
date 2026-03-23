import { test, expect } from "@playwright/test";
import { existsSync, readFileSync } from "fs";
import { resolve } from "path";
import { getAnyTenantKey, pollJob } from "../helpers";

const TEST_PDF = resolve(
  __dirname,
  "../../../../packages/engine/tests/fixtures/test-sample.pdf",
);

test.describe("Preflight Jobs", () => {
  let apiKey: string;

  test.beforeAll(() => {
    apiKey = getAnyTenantKey();
  });

  test("POST /api/v1/jobs submits a PDF and returns 202", async ({
    request,
  }) => {
    test.skip(!apiKey, "No test credentials");
    test.skip(!existsSync(TEST_PDF), "Test PDF not found");

    const res = await request.post("/api/v1/jobs", {
      headers: { Authorization: `Bearer ${apiKey}` },
      multipart: {
        file: {
          name: "test-sample.pdf",
          mimeType: "application/pdf",
          buffer: readFileSync(TEST_PDF),
        },
      },
    });
    expect(res.status()).toBe(202);
    const body = await res.json();
    expect(body).toHaveProperty("job_id");
    expect(body.status).toBe("pending");

    // Check rate limit headers
    const headers = res.headers();
    expect(headers["x-ratelimit-limit"]).toBeDefined();
    expect(headers["x-ratelimit-remaining"]).toBeDefined();
  });

  test("GET /api/v1/jobs lists jobs for tenant", async ({ request }) => {
    test.skip(!apiKey, "No test credentials");

    const res = await request.get("/api/v1/jobs", {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("jobs");
    expect(body).toHaveProperty("total");
    expect(body).toHaveProperty("page");
    expect(Array.isArray(body.jobs)).toBe(true);
  });

  test("full job lifecycle: submit → poll → complete → delete", async ({
    request,
  }) => {
    test.skip(!apiKey, "No test credentials");
    test.skip(!existsSync(TEST_PDF), "Test PDF not found");

    // Submit
    const submitRes = await request.post("/api/v1/jobs", {
      headers: { Authorization: `Bearer ${apiKey}` },
      multipart: {
        file: {
          name: "lifecycle-test.pdf",
          mimeType: "application/pdf",
          buffer: readFileSync(TEST_PDF),
        },
        profile_id: "lintpdf-default",
      },
    });
    expect(submitRes.status()).toBe(202);
    const { job_id: jobId } = await submitRes.json();

    // Poll until complete
    const result = await pollJob(request, jobId, apiKey, 60_000);
    expect(["complete", "failed"]).toContain(result.status);

    if (result.status === "complete") {
      expect(result).toHaveProperty("summary");
      expect(result).toHaveProperty("findings");
    }

    // Delete
    const delRes = await request.delete(`/api/v1/jobs/${jobId}`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    expect([200, 204]).toContain(delRes.status());
  });

  test("GET /api/v1/jobs/:id returns 404 for non-existent job", async ({
    request,
  }) => {
    test.skip(!apiKey, "No test credentials");

    const res = await request.get(
      "/api/v1/jobs/00000000-0000-0000-0000-000000000000",
      { headers: { Authorization: `Bearer ${apiKey}` } },
    );
    expect(res.status()).toBe(404);
  });
});
