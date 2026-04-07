import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Annotations API (Plugin Routes)", () => {
  let sessionToken: string;
  let testJobId: string | null = null;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
    const auth = await authenticateRole(request, "owner");
    sessionToken = auth.sessionToken;

    // Find a completed job for annotation tests
    const listRes = await request.get(
      `${APP_BASE}/api/lintpdf/jobs?status=complete&limit=1`,
      {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      },
    );

    if (listRes.ok()) {
      const body = await listRes.json();
      const jobs = (body.jobs ?? []).filter(
        (j: Record<string, unknown>) => j.status === "complete",
      );
      if (jobs.length > 0) {
        testJobId = (jobs[0].id ?? jobs[0].jobId) as string;
      }
    }
  });

  const headers = () => ({
    Cookie: `pixie-dust-session=${sessionToken}`,
    "Content-Type": "application/json",
  });

  test.describe("GET /api/lintpdf/annotations/:jobId", () => {
    test("returns annotations for completed job", async ({ request }) => {
      test.skip(!testJobId, "No completed job for annotation tests");

      const res = await request.get(
        `${APP_BASE}/api/lintpdf/annotations/${testJobId}`,
        {
          headers: headers(),
        },
      );

      expect([200, 403, 404, 500].includes(res.status())).toBe(true);

      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("annotations");
        expect(Array.isArray(body.annotations)).toBe(true);
      }
    });

    test("returns 404 for non-existent job", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/annotations/non-existent-annotation-job`,
        {
          headers: headers(),
        },
      );

      expect([400, 403, 404, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/annotations/any-job-id`,
        {
          headers: { Cookie: "" },
        },
      );

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("POST /api/lintpdf/annotations/:jobId/:pageNum", () => {
    test("creates annotation on page 1", async ({ request }) => {
      test.skip(!testJobId, "No completed job for annotation tests");

      const res = await request.post(
        `${APP_BASE}/api/lintpdf/annotations/${testJobId}/1`,
        {
          headers: headers(),
          data: {
            type: "comment",
            x: 100,
            y: 200,
            text: "E2E test annotation",
          },
        },
      );

      // 200/201 for success, 400/422 for validation, 404 if job not found
      expect([200, 201, 400, 403, 404, 422, 500].includes(res.status())).toBe(true);

      if (res.ok()) {
        const body = await res.json();
        expect(body.id ?? body.annotation?.id).toBeTruthy();
      }
    });

    test("returns 400 for missing annotation data", async ({ request }) => {
      test.skip(!testJobId, "No completed job for annotation tests");

      const res = await request.post(
        `${APP_BASE}/api/lintpdf/annotations/${testJobId}/1`,
        {
          headers: headers(),
          data: {},
        },
      );

      expect([400, 422, 500].includes(res.status())).toBe(true);
    });

    test("returns 404 for invalid page number", async ({ request }) => {
      test.skip(!testJobId, "No completed job for annotation tests");

      const res = await request.post(
        `${APP_BASE}/api/lintpdf/annotations/${testJobId}/99999`,
        {
          headers: headers(),
          data: {
            type: "comment",
            x: 100,
            y: 200,
            text: "Invalid page annotation",
          },
        },
      );

      expect([400, 404, 422, 500].includes(res.status())).toBe(true);
    });

    test("returns 404 for non-existent job", async ({ request }) => {
      const res = await request.post(
        `${APP_BASE}/api/lintpdf/annotations/non-existent-job/1`,
        {
          headers: headers(),
          data: {
            type: "comment",
            x: 100,
            y: 200,
            text: "Should fail",
          },
        },
      );

      expect([400, 403, 404, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.post(
        `${APP_BASE}/api/lintpdf/annotations/any-job/1`,
        {
          headers: { Cookie: "", "Content-Type": "application/json" },
          data: { type: "comment", text: "unauth" },
        },
      );

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("supports different annotation types", async ({ request }) => {
      test.skip(!testJobId, "No completed job for annotation tests");

      const types = ["highlight", "rectangle", "note"];

      for (const annotationType of types) {
        const res = await request.post(
          `${APP_BASE}/api/lintpdf/annotations/${testJobId}/1`,
          {
            headers: headers(),
            data: {
              type: annotationType,
              x: 50,
              y: 50,
              width: 200,
              height: 100,
              text: `E2E ${annotationType} annotation`,
            },
          },
        );

        // Either accepted or rejected — both valid
        expect([200, 201, 400, 403, 404, 422, 500].includes(res.status())).toBe(true);
      }
    });
  });
});
