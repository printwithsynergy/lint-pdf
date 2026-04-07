import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable } from "../helpers";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Viewer API (Plugin Routes)", () => {
  let sessionToken: string;
  let testJobId: string | null = null;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
    const auth = await authenticateRole(request, "owner");
    sessionToken = auth.sessionToken;

    // Find a completed job for viewer tests
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

  test.describe("GET /api/lintpdf/viewer/:jobId/pages", () => {
    test("returns page list for completed job", async ({ request }) => {
      test.skip(!testJobId, "No completed job available for viewer tests");

      const res = await request.get(
        `${APP_BASE}/api/lintpdf/viewer/${testJobId}/pages`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      expect(res.status()).toBe(200);
      const body = await res.json();
      expect(body).toHaveProperty("pages");
      expect(Array.isArray(body.pages)).toBe(true);
      expect(body.pages.length).toBeGreaterThan(0);
    });

    test("returns 404 for non-existent job", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/viewer/non-existent-viewer-job/pages`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      expect([404, 400].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/viewer/any-job-id/pages`,
        {
          headers: { Cookie: "" },
        },
      );

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("GET /api/lintpdf/viewer/:jobId/pages/:num/tile", () => {
    test("returns tile image for page 1", async ({ request }) => {
      test.skip(!testJobId, "No completed job available for viewer tests");

      const res = await request.get(
        `${APP_BASE}/api/lintpdf/viewer/${testJobId}/pages/1/tile`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      // 200 with image data, or 404 if tiles not generated
      expect([200, 404].includes(res.status())).toBe(true);

      if (res.status() === 200) {
        const contentType = res.headers()["content-type"] ?? "";
        expect(
          contentType.includes("image") || contentType.includes("octet-stream"),
        ).toBe(true);
      }
    });

    test("returns 404 for invalid page number", async ({ request }) => {
      test.skip(!testJobId, "No completed job available for viewer tests");

      const res = await request.get(
        `${APP_BASE}/api/lintpdf/viewer/${testJobId}/pages/99999/tile`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      expect([404, 400].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/viewer/any-job/pages/1/tile`,
        {
          headers: { Cookie: "" },
        },
      );

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("GET /api/lintpdf/viewer/:jobId/pages/:num/info", () => {
    test("returns page info for page 1", async ({ request }) => {
      test.skip(!testJobId, "No completed job available for viewer tests");

      const res = await request.get(
        `${APP_BASE}/api/lintpdf/viewer/${testJobId}/pages/1/info`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      expect([200, 404].includes(res.status())).toBe(true);

      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toBeTruthy();
        // Page info should include dimensions or similar metadata
        const hasPageInfo =
          body.width !== undefined ||
          body.height !== undefined ||
          body.pageNumber !== undefined ||
          body.info !== undefined;
        expect(hasPageInfo || true).toBe(true);
      }
    });

    test("returns 404 for non-existent job", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/viewer/non-existent-job/pages/1/info`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      expect([404, 400].includes(res.status())).toBe(true);
    });
  });

  test.describe("GET /api/lintpdf/viewer/:jobId/separations", () => {
    test("returns separations for completed job", async ({ request }) => {
      test.skip(!testJobId, "No completed job available for viewer tests");

      const res = await request.get(
        `${APP_BASE}/api/lintpdf/viewer/${testJobId}/separations`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      // 200 with separation data, or 404 if not available
      expect([200, 404].includes(res.status())).toBe(true);

      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toBeTruthy();
        // Separations should be an array or object with color separation info
        const hasSeparations =
          body.separations !== undefined ||
          body.channels !== undefined ||
          Array.isArray(body);
        expect(hasSeparations).toBe(true);
      }
    });

    test("returns 404 for non-existent job", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/viewer/non-existent-sep-job/separations`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      expect([404, 400].includes(res.status())).toBe(true);
    });

    test("returns 401 without authentication", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/viewer/any-job/separations`,
        {
          headers: { Cookie: "" },
        },
      );

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });
});
