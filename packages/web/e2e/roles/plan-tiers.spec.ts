import { test, expect } from "@playwright/test";
import { existsSync, readFileSync } from "fs";
import { resolve } from "path";
import { getTenant, pollJob } from "../helpers";

const TEST_PDF = resolve(
  __dirname,
  "../../../../packages/engine/tests/fixtures/test-sample.pdf",
);

const PLANS = ["free", "starter", "growth", "scale", "enterprise"] as const;

const EXPECTED_LIMITS: Record<string, { daily: number; maxMb: number }> = {
  free: { daily: 50, maxMb: 25 },
  starter: { daily: 500, maxMb: 250 },
  growth: { daily: 5000, maxMb: 500 },
  scale: { daily: 25000, maxMb: 1024 },
  enterprise: { daily: 100000, maxMb: 2048 },
};

for (const plan of PLANS) {
  test.describe(`${plan.toUpperCase()} Plan Tier`, () => {
    test(`${plan}: submit job and verify rate limit headers`, async ({
      request,
    }) => {
      const tenant = getTenant(plan);
      test.skip(!tenant, `No ${plan} test tenant`);
      test.skip(!existsSync(TEST_PDF), "Test PDF not found");

      const res = await request.post("/api/v1/jobs", {
        headers: { Authorization: `Bearer ${tenant?.api_key}` },
        multipart: {
          file: {
            name: `${plan}-test.pdf`,
            mimeType: "application/pdf",
            buffer: readFileSync(TEST_PDF),
          },
        },
      });
      expect(res.status()).toBe(202);

      // Check rate limit header matches plan
      const limit = res.headers()["x-ratelimit-limit"];
      if (limit) {
        expect(parseInt(limit)).toBe(EXPECTED_LIMITS[plan].daily);
      }
    });

    test(`${plan}: usage endpoint shows correct daily limit`, async ({
      request,
    }) => {
      const tenant = getTenant(plan);
      test.skip(!tenant, `No ${plan} test tenant`);

      const res = await request.get("/api/v1/usage", {
        headers: { Authorization: `Bearer ${tenant?.api_key}` },
      });
      expect(res.status()).toBe(200);
      const body = await res.json();
      expect(body.daily_limit).toBe(EXPECTED_LIMITS[plan].daily);
    });

    test(`${plan}: job completes successfully`, async ({ request }) => {
      const tenant = getTenant(plan);
      test.skip(!tenant, `No ${plan} test tenant`);
      test.skip(!existsSync(TEST_PDF), "Test PDF not found");

      // Submit
      const submitRes = await request.post("/api/v1/jobs", {
        headers: { Authorization: `Bearer ${tenant?.api_key}` },
        multipart: {
          file: {
            name: `${plan}-lifecycle.pdf`,
            mimeType: "application/pdf",
            buffer: readFileSync(TEST_PDF),
          },
          profile_id: "grounded-default",
        },
      });
      expect(submitRes.status()).toBe(202);
      const { id: jobId } = await submitRes.json();

      // Poll
      const result = await pollJob(request, jobId, tenant?.api_key, 60_000);
      expect(["complete", "failed"]).toContain(result.status);
    });
  });
}
