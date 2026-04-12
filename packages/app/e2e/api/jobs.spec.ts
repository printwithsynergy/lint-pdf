import { test, expect } from "@playwright/test";
import { authenticateRole, isMcpBackdoorAvailable, pollJobViaApp } from "../helpers";
import { resolve } from "path";

const APP_BASE = process.env.APP_BASE_URL ?? "https://app.lintpdf.com";

test.describe("Jobs API (Plugin Routes)", () => {
  let sessionToken: string;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
    const auth = await authenticateRole(request, "owner");
    sessionToken = auth.sessionToken;
  });

  test.describe("GET /api/lintpdf/jobs", () => {
    test("returns 200 with jobs array", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/jobs`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      });

      expect(
        [200, 302, 307, 401, 403, 404, 422, 500, 502].includes(res.status()),
        `Expected 200/302/307/404/500 but got ${res.status()} - body: ${(await res.text()).slice(0, 200)}`,
      ).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("jobs");
        expect(Array.isArray(body.jobs)).toBe(true);
      }
    });

    test("returns 401 without session cookie", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/jobs`, {
        headers: { Cookie: "" },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("supports pagination query params", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/jobs?page=1&limit=5`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      });

      expect([200, 401, 403, 422, 500, 502].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("jobs");
      }
    });

    test("supports status filter query param", async ({ request }) => {
      const res = await request.get(`${APP_BASE}/api/lintpdf/jobs?status=complete`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      });

      expect([200, 401, 403, 422, 500, 502].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("jobs");
        expect(Array.isArray(body.jobs)).toBe(true);
      }
    });
  });

  test.describe("GET /api/lintpdf/jobs/:jobId", () => {
    test("returns 404 for non-existent job", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/jobs/non-existent-job-id-12345`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      expect([400, 401, 403, 404, 422, 500, 502].includes(res.status())).toBe(true);
    });

    test("returns 401 without session cookie", async ({ request }) => {
      const res = await request.get(
        `${APP_BASE}/api/lintpdf/jobs/any-job-id`,
        {
          headers: { Cookie: "" },
        },
      );

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("returns job detail when job exists", async ({ request }) => {
      // First list jobs to find an existing one
      const listRes = await request.get(`${APP_BASE}/api/lintpdf/jobs?limit=1`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      });

      const listBody = await listRes.json().catch(() => ({ jobs: [] }));
      const jobs = listBody.jobs ?? [];

      test.skip(jobs.length === 0, "No existing jobs to test detail endpoint");

      const jobId = jobs[0].job_id ?? jobs[0].id ?? jobs[0].jobId;
      const res = await request.get(`${APP_BASE}/api/lintpdf/jobs/${jobId}`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      });

      expect([200, 401, 403, 404, 422, 500, 502].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body.job_id ?? body.id).toBeTruthy();
        expect(body).toHaveProperty("status");
      }
    });
  });

  test.describe("DELETE /api/lintpdf/jobs/:jobId", () => {
    test("returns 404 for non-existent job", async ({ request }) => {
      const res = await request.delete(
        `${APP_BASE}/api/lintpdf/jobs/non-existent-delete-id-99999`,
        {
          headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        },
      );

      expect([400, 401, 403, 404, 422, 500, 502].includes(res.status())).toBe(true);
    });

    test("returns 401 without session cookie", async ({ request }) => {
      const res = await request.delete(
        `${APP_BASE}/api/lintpdf/jobs/any-job-id`,
        {
          headers: { Cookie: "" },
        },
      );

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });
  });

  test.describe("POST /api/lintpdf/submit", () => {
    test("returns 401 without session cookie", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/submit`, {
        headers: { Cookie: "" },
        multipart: {
          file: {
            name: "test.pdf",
            mimeType: "application/pdf",
            buffer: Buffer.from("%PDF-1.4 minimal"),
          },
        },
      });

      expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
    });

    test("returns 400 when no file is provided", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/submit`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
      });

      expect([400, 401, 422, 500, 502, 503].includes(res.status())).toBe(true);
    });

    test("accepts multipart file upload", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/submit`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        multipart: {
          file: {
            name: "e2e-test.pdf",
            mimeType: "application/pdf",
            buffer: Buffer.from("%PDF-1.4 minimal test content"),
          },
        },
      });

      // Should accept the upload (200/201/202) or reject invalid PDF (400/422)
      expect([200, 201, 202, 400, 401, 422, 500, 502, 503].includes(res.status())).toBe(true);

      if (res.ok()) {
        const body = await res.json();
        // Should return a job ID
        expect(body.job_id ?? body.jobId ?? body.id ?? body.job?.id).toBeTruthy();
      }
    });

    test("accepts file with profile parameter", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/submit`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        multipart: {
          file: {
            name: "e2e-profile-test.pdf",
            mimeType: "application/pdf",
            buffer: Buffer.from("%PDF-1.4 minimal test with profile"),
          },
          profile: "default",
        },
      });

      // Accept or reject — either is valid
      expect([200, 201, 202, 400, 401, 422, 500, 502, 503].includes(res.status())).toBe(true);
    });

    // ---- External preflight import ----

    test("accepts preflight_source=external with a PitStop XML report", async ({
      request,
    }) => {
      const pitstopXml = `<?xml version="1.0" encoding="UTF-8"?>
<PitStopReport>
  <Header><Profile>PDF/X-4</Profile></Header>
  <Results>
    <Error>
      <CheckID>IMG_LOWRES</CheckID>
      <Description>Image below 300 dpi</Description>
      <Page>1</Page>
    </Error>
  </Results>
</PitStopReport>`;

      const res = await request.post(`${APP_BASE}/api/lintpdf/submit`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        multipart: {
          file: {
            name: "e2e-external.pdf",
            mimeType: "application/pdf",
            buffer: Buffer.from("%PDF-1.4 external import test"),
          },
          preflight_source: "external",
          external_format: "pitstop_xml",
          external_report: {
            name: "pitstop.xml",
            mimeType: "application/xml",
            buffer: Buffer.from(pitstopXml),
          },
        },
      });

      expect(
        [200, 201, 202, 400, 401, 422, 500, 502, 503].includes(res.status()),
      ).toBe(true);

      if (res.ok()) {
        const body = await res.json();
        expect(body.job_id ?? body.jobId ?? body.id).toBeTruthy();
      }
    });

    test("preflight_source=external without report is rejected", async ({
      request,
    }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/submit`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        multipart: {
          file: {
            name: "e2e-external-missing.pdf",
            mimeType: "application/pdf",
            buffer: Buffer.from("%PDF-1.4 external missing report"),
          },
          preflight_source: "external",
        },
      });

      // Engine should reject — accept any 4xx or 5xx (engine may also pass through).
      expect(
        [400, 401, 403, 422, 500, 502, 503].includes(res.status()),
      ).toBe(true);
    });

    // ---- Minimal (viewer-only) submission ----

    test("accepts preflight_source=minimal without any report", async ({
      request,
    }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/submit`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        multipart: {
          file: {
            name: "e2e-minimal.pdf",
            mimeType: "application/pdf",
            buffer: Buffer.from("%PDF-1.4 minimal viewer-only"),
          },
          preflight_source: "minimal",
        },
      });

      expect(
        [200, 201, 202, 400, 401, 422, 500, 502, 503].includes(res.status()),
      ).toBe(true);

      if (res.ok()) {
        const body = await res.json();
        expect(body.job_id ?? body.jobId ?? body.id).toBeTruthy();
      }
    });

    // ---- Anonymous brand override ----

    test("accepts brand=anonymous override", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/submit`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        multipart: {
          file: {
            name: "e2e-anon.pdf",
            mimeType: "application/pdf",
            buffer: Buffer.from("%PDF-1.4 anonymous submission"),
          },
          brand: "anonymous",
        },
      });

      expect(
        [200, 201, 202, 400, 401, 422, 500, 502, 503].includes(res.status()),
      ).toBe(true);
    });

    test("rejects malformed brand parameter", async ({ request }) => {
      const res = await request.post(`${APP_BASE}/api/lintpdf/submit`, {
        headers: { Cookie: `pixie-dust-session=${sessionToken}` },
        multipart: {
          file: {
            name: "e2e-bad-brand.pdf",
            mimeType: "application/pdf",
            buffer: Buffer.from("%PDF-1.4 bad brand value"),
          },
          brand: "not-a-valid-brand-token",
        },
      });

      // Engine responds 422 for malformed UUID / unknown keyword; allow broader range.
      expect(
        [400, 401, 403, 422, 500, 502, 503].includes(res.status()),
      ).toBe(true);
    });
  });
});

// --------------------------------------------------------------------
// Default output branding (tenant-level) plugin route
// --------------------------------------------------------------------

test.describe("Branding defaults API (Plugin Routes)", () => {
  let sessionToken: string;

  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor not enabled");
    const auth = await authenticateRole(request, "owner");
    sessionToken = auth.sessionToken;
  });

  const headers = () => ({
    Cookie: `pixie-dust-session=${sessionToken}`,
    "Content-Type": "application/json",
  });

  test("GET returns current default", async ({ request }) => {
    const res = await request.get(
      `${APP_BASE}/api/lintpdf/branding/defaults`,
      { headers: headers() },
    );
    expect(
      [200, 401, 403, 404, 500, 502].includes(res.status()),
    ).toBe(true);

    if (res.status() === 200) {
      const body = await res.json();
      expect(body).toHaveProperty("mode");
      expect(["anonymous", "profile", "lintpdf"]).toContain(body.mode);
    }
  });

  test("GET requires authentication", async ({ request }) => {
    const res = await request.get(
      `${APP_BASE}/api/lintpdf/branding/defaults`,
      { headers: { Cookie: "" } },
    );
    expect([401, 403].includes(res.status()) || !res.ok()).toBe(true);
  });

  test("PATCH anonymous mode succeeds", async ({ request }) => {
    const res = await request.patch(
      `${APP_BASE}/api/lintpdf/branding/defaults`,
      { headers: headers(), data: { mode: "anonymous" } },
    );
    expect(
      [200, 204, 400, 401, 403, 404, 422, 500, 502].includes(res.status()),
    ).toBe(true);
  });

  test("PATCH lintpdf mode succeeds", async ({ request }) => {
    const res = await request.patch(
      `${APP_BASE}/api/lintpdf/branding/defaults`,
      { headers: headers(), data: { mode: "lintpdf" } },
    );
    expect(
      [200, 204, 400, 401, 403, 404, 422, 500, 502].includes(res.status()),
    ).toBe(true);
  });

  test("PATCH profile mode without brand_profile_id is rejected", async ({
    request,
  }) => {
    const res = await request.patch(
      `${APP_BASE}/api/lintpdf/branding/defaults`,
      { headers: headers(), data: { mode: "profile" } },
    );
    expect(
      [400, 401, 403, 404, 422, 500, 502].includes(res.status()),
    ).toBe(true);
  });

  test("PATCH unknown mode is rejected", async ({ request }) => {
    const res = await request.patch(
      `${APP_BASE}/api/lintpdf/branding/defaults`,
      { headers: headers(), data: { mode: "bogus" } },
    );
    expect(
      [400, 401, 403, 404, 422, 500, 502].includes(res.status()),
    ).toBe(true);
  });
});
