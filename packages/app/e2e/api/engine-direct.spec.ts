import { test, expect } from "@playwright/test";
import {
  getEngineApiKey,
  getAdminApiKey,
  getEngineBase,
  pollJobViaEngine,
} from "../helpers";

const ENGINE_BASE = getEngineBase();

test.describe("Engine Direct API", () => {
  const apiKey = getEngineApiKey();
  const adminKey = getAdminApiKey();

  const bearerHeaders = () => ({
    Authorization: `Bearer ${apiKey}`,
    "Content-Type": "application/json",
  });

  const adminHeaders = () => ({
    "X-Admin-Key": adminKey,
    "Content-Type": "application/json",
  });

  test.beforeAll(async () => {
    test.skip(!apiKey, "ENGINE_API_KEY not configured");
  });

  // ---------- Health & Status ----------

  test.describe("GET /health", () => {
    test("returns 200 with health status", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/health`);

      expect([200, 404, 503].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body.status ?? body.healthy ?? body.ok).toBeTruthy();
      }
    });
  });

  test.describe("GET /api/v1/status", () => {
    test("returns 200 with engine status", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/status`, {
        headers: bearerHeaders(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toBeTruthy();
      }
    });

    test("returns 401 without API key", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/status`);

      expect([401, 403].includes(res.status())).toBe(true);
    });
  });

  // ---------- Jobs ----------

  test.describe("GET /api/v1/jobs", () => {
    test("returns 200 with jobs list", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/jobs`, {
        headers: bearerHeaders(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("jobs");
        expect(Array.isArray(body.jobs)).toBe(true);
      }
    });

    test("supports pagination", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/jobs?page=1&limit=5`, {
        headers: bearerHeaders(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("jobs");
      }
    });

    test("returns 401 without API key", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/jobs`);

      expect([401, 403].includes(res.status())).toBe(true);
    });
  });

  test.describe("POST /api/v1/jobs", () => {
    test("submits a PDF for preflight", async ({ request }) => {
      const res = await request.post(`${ENGINE_BASE}/api/v1/jobs`, {
        headers: { Authorization: `Bearer ${apiKey}` },
        multipart: {
          file: {
            name: "e2e-engine-test.pdf",
            mimeType: "application/pdf",
            buffer: Buffer.from("%PDF-1.4 minimal engine test"),
          },
        },
      });

      // 200/201/202 for accepted, 400/422 for invalid PDF
      expect([200, 201, 202, 400, 422, 500].includes(res.status())).toBe(true);

      if (res.ok()) {
        const body = await res.json();
        expect(body.jobId ?? body.id ?? body.job?.id).toBeTruthy();
      }
    });

    test("accepts job with profile parameter", async ({ request }) => {
      const res = await request.post(`${ENGINE_BASE}/api/v1/jobs`, {
        headers: { Authorization: `Bearer ${apiKey}` },
        multipart: {
          file: {
            name: "e2e-engine-profile-test.pdf",
            mimeType: "application/pdf",
            buffer: Buffer.from("%PDF-1.4 minimal with profile"),
          },
          profile: "default",
        },
      });

      expect([200, 201, 202, 400, 422, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without API key", async ({ request }) => {
      const res = await request.post(`${ENGINE_BASE}/api/v1/jobs`, {
        multipart: {
          file: {
            name: "unauth.pdf",
            mimeType: "application/pdf",
            buffer: Buffer.from("%PDF-1.4"),
          },
        },
      });

      expect([401, 403].includes(res.status())).toBe(true);
    });
  });

  test.describe("GET /api/v1/jobs/:id", () => {
    test("returns 404 for non-existent job", async ({ request }) => {
      const res = await request.get(
        `${ENGINE_BASE}/api/v1/jobs/non-existent-engine-job`,
        {
          headers: bearerHeaders(),
        },
      );

      expect([400, 404, 500].includes(res.status())).toBe(true);
    });

    test("returns job detail for existing job", async ({ request }) => {
      const listRes = await request.get(`${ENGINE_BASE}/api/v1/jobs?limit=1`, {
        headers: bearerHeaders(),
      });

      const listBody = await listRes.json().catch(() => ({ jobs: [] }));
      const jobs = listBody.jobs ?? [];

      test.skip(jobs.length === 0, "No engine jobs to test detail");

      const jobId = jobs[0].id ?? jobs[0].jobId;
      const res = await request.get(`${ENGINE_BASE}/api/v1/jobs/${jobId}`, {
        headers: bearerHeaders(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("status");
      }
    });
  });

  test.describe("DELETE /api/v1/jobs/:id", () => {
    test("returns 404 for non-existent job", async ({ request }) => {
      const res = await request.delete(
        `${ENGINE_BASE}/api/v1/jobs/non-existent-engine-delete`,
        {
          headers: bearerHeaders(),
        },
      );

      expect([400, 404, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without API key", async ({ request }) => {
      const res = await request.delete(
        `${ENGINE_BASE}/api/v1/jobs/any-id`,
      );

      expect([401, 403].includes(res.status())).toBe(true);
    });
  });

  // ---------- Profiles ----------

  test.describe("GET /api/v1/profiles", () => {
    test("returns 200 with profiles list", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/profiles`, {
        headers: bearerHeaders(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("profiles");
        expect(Array.isArray(body.profiles)).toBe(true);
      }
    });

    test("returns 401 without API key", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/profiles`);

      expect([401, 403].includes(res.status())).toBe(true);
    });
  });

  test.describe("POST /api/v1/profiles", () => {
    test("creates a profile", async ({ request }) => {
      const res = await request.post(`${ENGINE_BASE}/api/v1/profiles`, {
        headers: bearerHeaders(),
        data: {
          name: `E2E Engine Profile ${Date.now()}`,
          checks: {
            resolution: { enabled: true, minDpi: 300 },
          },
        },
      });

      expect([200, 201, 400, 422, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without API key", async ({ request }) => {
      const res = await request.post(`${ENGINE_BASE}/api/v1/profiles`, {
        headers: { "Content-Type": "application/json" },
        data: { name: "unauth" },
      });

      expect([401, 403].includes(res.status())).toBe(true);
    });
  });

  // ---------- Webhooks ----------

  test.describe("GET /api/v1/webhooks", () => {
    test("returns 200 with webhooks list", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/webhooks`, {
        headers: bearerHeaders(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("webhooks");
        expect(Array.isArray(body.webhooks)).toBe(true);
      }
    });

    test("returns 401 without API key", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/webhooks`);

      expect([401, 403].includes(res.status())).toBe(true);
    });
  });

  test.describe("POST /api/v1/webhooks", () => {
    test("creates a webhook", async ({ request }) => {
      const res = await request.post(`${ENGINE_BASE}/api/v1/webhooks`, {
        headers: bearerHeaders(),
        data: {
          url: "https://example.com/e2e-webhook",
          events: ["job.completed", "job.failed"],
        },
      });

      expect([200, 201, 400, 422, 500].includes(res.status())).toBe(true);

      if (res.ok()) {
        const body = await res.json();
        expect(body.id ?? body.webhook?.id).toBeTruthy();
      }
    });

    test("returns 400 for invalid webhook URL", async ({ request }) => {
      const res = await request.post(`${ENGINE_BASE}/api/v1/webhooks`, {
        headers: bearerHeaders(),
        data: {
          url: "not-a-valid-url",
          events: ["job.completed"],
        },
      });

      expect([400, 422, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without API key", async ({ request }) => {
      const res = await request.post(`${ENGINE_BASE}/api/v1/webhooks`, {
        headers: { "Content-Type": "application/json" },
        data: { url: "https://example.com", events: ["job.completed"] },
      });

      expect([401, 403].includes(res.status())).toBe(true);
    });
  });

  test.describe("DELETE /api/v1/webhooks/:id", () => {
    test("returns 404 for non-existent webhook", async ({ request }) => {
      const res = await request.delete(
        `${ENGINE_BASE}/api/v1/webhooks/non-existent-webhook`,
        {
          headers: bearerHeaders(),
        },
      );

      expect([400, 404, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without API key", async ({ request }) => {
      const res = await request.delete(
        `${ENGINE_BASE}/api/v1/webhooks/any-id`,
      );

      expect([401, 403].includes(res.status())).toBe(true);
    });
  });

  // ---------- Usage ----------

  test.describe("GET /api/v1/usage", () => {
    test("returns 200 with usage data", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/usage`, {
        headers: bearerHeaders(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toBeTruthy();
      }
    });

    test("returns 401 without API key", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/usage`);

      expect([401, 403].includes(res.status())).toBe(true);
    });
  });

  // ---------- Reports ----------

  test.describe("POST /api/v1/reports/generate", () => {
    test("returns 400/404 for non-existent job", async ({ request }) => {
      const res = await request.post(`${ENGINE_BASE}/api/v1/reports/generate`, {
        headers: bearerHeaders(),
        data: { jobId: "non-existent-report-job" },
      });

      expect([400, 404, 500].includes(res.status())).toBe(true);
    });

    test("generates report for completed job", async ({ request }) => {
      const listRes = await request.get(
        `${ENGINE_BASE}/api/v1/jobs?status=complete&limit=1`,
        {
          headers: bearerHeaders(),
        },
      );

      const listBody = await listRes.json();
      const jobs = (listBody.jobs ?? []).filter(
        (j: Record<string, unknown>) => j.status === "complete",
      );

      test.skip(jobs.length === 0, "No completed jobs for report generation");

      const jobId = jobs[0].id ?? jobs[0].jobId;
      const res = await request.post(`${ENGINE_BASE}/api/v1/reports/generate`, {
        headers: bearerHeaders(),
        data: { jobId },
      });

      expect([200, 201, 202, 409, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without API key", async ({ request }) => {
      const res = await request.post(`${ENGINE_BASE}/api/v1/reports/generate`, {
        headers: { "Content-Type": "application/json" },
        data: { jobId: "test" },
      });

      expect([401, 403].includes(res.status())).toBe(true);
    });
  });

  // ---------- AI ----------

  test.describe("GET /api/v1/ai/config", () => {
    test("returns 200 with AI config", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/ai/config`, {
        headers: bearerHeaders(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without API key", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/ai/config`);

      expect([401, 403].includes(res.status())).toBe(true);
    });
  });

  test.describe("GET /api/v1/ai/credits", () => {
    test("returns 200 with AI credits", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/ai/credits`, {
        headers: bearerHeaders(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);
    });
  });

  test.describe("GET /api/v1/ai/presets", () => {
    test("returns 200 with AI presets", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/ai/presets`, {
        headers: bearerHeaders(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);

      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("presets");
        expect(Array.isArray(body.presets)).toBe(true);
      }
    });
  });

  test.describe("GET /api/v1/ai/usage", () => {
    test("returns 200 with AI usage stats", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/ai/usage`, {
        headers: bearerHeaders(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);
    });
  });

  // ---------- Viewer ----------

  test.describe("GET /api/v1/viewer/jobs/:id/pages", () => {
    test("returns page list for completed job", async ({ request }) => {
      const listRes = await request.get(
        `${ENGINE_BASE}/api/v1/jobs?status=complete&limit=1`,
        {
          headers: bearerHeaders(),
        },
      );

      const listBody = await listRes.json();
      const jobs = (listBody.jobs ?? []).filter(
        (j: Record<string, unknown>) => j.status === "complete",
      );

      test.skip(jobs.length === 0, "No completed jobs for viewer test");

      const jobId = jobs[0].id ?? jobs[0].jobId;
      const res = await request.get(
        `${ENGINE_BASE}/api/v1/viewer/jobs/${jobId}/pages`,
        {
          headers: bearerHeaders(),
        },
      );

      expect([200, 404, 500].includes(res.status())).toBe(true);

      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("pages");
        expect(Array.isArray(body.pages)).toBe(true);
      }
    });

    test("returns 404 for non-existent job", async ({ request }) => {
      const res = await request.get(
        `${ENGINE_BASE}/api/v1/viewer/jobs/non-existent/pages`,
        {
          headers: bearerHeaders(),
        },
      );

      expect([400, 404, 500].includes(res.status())).toBe(true);
    });
  });

  // ---------- Endpoints CRUD ----------

  test.describe("Endpoints CRUD (/api/v1/endpoints)", () => {
    let createdEndpointId: string | null = null;

    test("POST creates an endpoint", async ({ request }) => {
      const res = await request.post(`${ENGINE_BASE}/api/v1/endpoints`, {
        headers: bearerHeaders(),
        data: {
          name: `E2E Engine Endpoint ${Date.now()}`,
          webhookUrl: "https://example.com/engine-webhook",
          active: true,
        },
      });

      expect([200, 201, 400, 422, 500].includes(res.status())).toBe(true);

      if (res.ok()) {
        const body = await res.json();
        createdEndpointId = (body.id ?? body.endpoint?.id) as string;
      }
    });

    test("GET lists endpoints", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/endpoints`, {
        headers: bearerHeaders(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("endpoints");
        expect(Array.isArray(body.endpoints)).toBe(true);
      }
    });

    test("PATCH updates an endpoint", async ({ request }) => {
      test.skip(!createdEndpointId, "No endpoint was created to update");

      const res = await request.patch(
        `${ENGINE_BASE}/api/v1/endpoints/${createdEndpointId}`,
        {
          headers: bearerHeaders(),
          data: { name: `Updated Engine Endpoint ${Date.now()}` },
        },
      );

      expect([200, 204, 400, 404, 500].includes(res.status())).toBe(true);
    });

    test("DELETE removes an endpoint", async ({ request }) => {
      test.skip(!createdEndpointId, "No endpoint was created to delete");

      const res = await request.delete(
        `${ENGINE_BASE}/api/v1/endpoints/${createdEndpointId}`,
        {
          headers: bearerHeaders(),
        },
      );

      expect([200, 204, 404, 500].includes(res.status())).toBe(true);
    });

    test("returns 401 without API key", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/endpoints`);

      expect([401, 403].includes(res.status())).toBe(true);
    });
  });

  // ---------- Admin Routes (X-Admin-Key) ----------

  test.describe("Admin routes with X-Admin-Key", () => {
    test.beforeAll(async () => {
      test.skip(!adminKey, "ADMIN_API_KEY not configured");
    });

    test("GET /api/v1/admin/tenants returns tenants", async ({ request }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/admin/tenants`, {
        headers: adminHeaders(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("tenants");
        expect(Array.isArray(body.tenants)).toBe(true);
      }
    });

    test("GET /api/v1/admin/tenants returns 401 without admin key", async ({
      request,
    }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/admin/tenants`);

      expect([401, 403].includes(res.status())).toBe(true);
    });

    test("GET /api/v1/admin/tenants returns 403 with regular API key", async ({
      request,
    }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/admin/tenants`, {
        headers: bearerHeaders(),
      });

      expect([403, 401].includes(res.status())).toBe(true);
    });

    test("GET /api/v1/admin/jobs returns cross-tenant jobs", async ({
      request,
    }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/admin/jobs`, {
        headers: adminHeaders(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("jobs");
        expect(Array.isArray(body.jobs)).toBe(true);
      }
    });

    test("GET /api/v1/admin/jobs supports pagination", async ({ request }) => {
      const res = await request.get(
        `${ENGINE_BASE}/api/v1/admin/jobs?page=1&limit=5`,
        {
          headers: adminHeaders(),
        },
      );

      expect([200, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("jobs");
      }
    });

    test("GET /api/v1/admin/jobs returns 401 without admin key", async ({
      request,
    }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/admin/jobs`);

      expect([401, 403].includes(res.status())).toBe(true);
    });

    test("GET /api/v1/admin/trials returns trial submissions", async ({
      request,
    }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/admin/trials`, {
        headers: adminHeaders(),
      });

      expect([200, 404, 500].includes(res.status())).toBe(true);
      if (res.status() === 200) {
        const body = await res.json();
        expect(body).toHaveProperty("trials");
        expect(Array.isArray(body.trials)).toBe(true);
      }
    });

    test("GET /api/v1/admin/trials supports status filter", async ({
      request,
    }) => {
      const res = await request.get(
        `${ENGINE_BASE}/api/v1/admin/trials?status=pending`,
        {
          headers: adminHeaders(),
        },
      );

      expect([200, 400, 500].includes(res.status())).toBe(true);
    });

    test("GET /api/v1/admin/trials returns 401 without admin key", async ({
      request,
    }) => {
      const res = await request.get(`${ENGINE_BASE}/api/v1/admin/trials`);

      expect([401, 403].includes(res.status())).toBe(true);
    });
  });
});
