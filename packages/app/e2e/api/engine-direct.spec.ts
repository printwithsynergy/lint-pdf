import { test, expect } from "@playwright/test";
import { readFileSync, existsSync } from "fs";
import { resolve } from "path";
import {
  isMcpBackdoorAvailable,
  getEngineApiKey,
  getAdminApiKey,
  getEngineBase,
  pollJobViaEngine,
} from "../helpers";

const TEST_PDF = resolve(__dirname, "../../../engine/tests/fixtures/test-sample.pdf");

test.describe("Engine Direct API — Health & Status", () => {
  test("GET /health returns ok", async ({ request }) => {
    const res = await request.get(`${getEngineBase()}/health`);
    expect(res.status()).toBe(200);
  });

  test("GET /api/v1/status returns service status", async ({ request }) => {
    const res = await request.get(`${getEngineBase()}/api/v1/status`);
    expect(res.status()).toBeLessThan(500);
  });
});

test.describe("Engine Direct API — Authenticated Endpoints", () => {
  const apiKey = () => getEngineApiKey();
  const authHeaders = () => ({ Authorization: `Bearer ${apiKey()}` });

  test.beforeAll(async () => {
    test.skip(!apiKey(), "No engine API key available");
  });

  // ---- Jobs ----
  test.describe("Jobs", () => {
    let createdJobId: string;

    test("POST /api/v1/jobs submits a preflight job", async ({ request }) => {
      test.skip(!existsSync(TEST_PDF), "Test PDF not found");

      const res = await request.post(`${getEngineBase()}/api/v1/jobs`, {
        headers: authHeaders(),
        multipart: {
          file: { name: "test.pdf", mimeType: "application/pdf", buffer: readFileSync(TEST_PDF) },
          profile_id: "lintpdf-default",
        },
      });
      expect(res.status()).toBe(202);
      const body = await res.json();
      expect(body).toHaveProperty("id");
      createdJobId = body.id;
    });

    test("GET /api/v1/jobs lists jobs", async ({ request }) => {
      const res = await request.get(`${getEngineBase()}/api/v1/jobs`, {
        headers: authHeaders(),
      });
      expect(res.status()).toBe(200);
      const body = await res.json();
      expect(Array.isArray(body.jobs ?? body)).toBe(true);
    });

    test("GET /api/v1/jobs/:id returns job details", async ({ request }) => {
      test.skip(!createdJobId, "No job created");

      const result = await pollJobViaEngine(request, createdJobId, apiKey(), 120_000);
      expect(["complete", "failed"]).toContain(result.status);
    });

    test("DELETE /api/v1/jobs/:id deletes job", async ({ request }) => {
      test.skip(!createdJobId, "No job created");

      const res = await request.delete(`${getEngineBase()}/api/v1/jobs/${createdJobId}`, {
        headers: authHeaders(),
      });
      expect([200, 204, 404]).toContain(res.status());
    });
  });

  // ---- Profiles ----
  test.describe("Profiles", () => {
    let customProfileId: string;

    test("GET /api/v1/profiles lists profiles", async ({ request }) => {
      const res = await request.get(`${getEngineBase()}/api/v1/profiles`, {
        headers: authHeaders(),
      });
      expect(res.status()).toBe(200);
      const body = await res.json();
      const profiles = body.profiles ?? body;
      expect(Array.isArray(profiles)).toBe(true);
      expect(profiles.length).toBeGreaterThan(0);
    });

    test("GET /api/v1/profiles/lintpdf-default returns profile", async ({ request }) => {
      const res = await request.get(`${getEngineBase()}/api/v1/profiles/lintpdf-default`, {
        headers: authHeaders(),
      });
      expect(res.status()).toBe(200);
    });

    test("POST /api/v1/profiles creates custom profile", async ({ request }) => {
      const res = await request.post(`${getEngineBase()}/api/v1/profiles`, {
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        data: {
          display_name: "E2E Test Profile",
          description: "Created by E2E tests",
          thresholds: { min_dpi: 150, tac_limit: 300 },
        },
      });
      if (res.status() === 201 || res.status() === 200) {
        const body = await res.json();
        customProfileId = body.profile_id ?? body.id;
      }
      expect(res.status()).toBeLessThan(500);
    });

    test("DELETE /api/v1/profiles/:id deletes custom profile", async ({ request }) => {
      test.skip(!customProfileId, "No custom profile created");

      const res = await request.delete(`${getEngineBase()}/api/v1/profiles/${customProfileId}`, {
        headers: authHeaders(),
      });
      expect([200, 204, 404]).toContain(res.status());
    });
  });

  // ---- Webhooks ----
  test.describe("Webhooks", () => {
    let webhookId: string;

    test("GET /api/v1/webhooks lists webhooks", async ({ request }) => {
      const res = await request.get(`${getEngineBase()}/api/v1/webhooks`, {
        headers: authHeaders(),
      });
      expect(res.status()).toBe(200);
    });

    test("POST /api/v1/webhooks creates webhook", async ({ request }) => {
      const res = await request.post(`${getEngineBase()}/api/v1/webhooks`, {
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        data: { url: "https://httpbin.org/post", events: ["job.complete"] },
      });
      if (res.ok()) {
        const body = await res.json();
        webhookId = body.id ?? body.webhook_id;
      }
      expect(res.status()).toBeLessThan(500);
    });

    test("DELETE /api/v1/webhooks/:id deletes webhook", async ({ request }) => {
      test.skip(!webhookId, "No webhook created");

      const res = await request.delete(`${getEngineBase()}/api/v1/webhooks/${webhookId}`, {
        headers: authHeaders(),
      });
      expect([200, 204, 404]).toContain(res.status());
    });
  });

  // ---- Reports ----
  test.describe("Reports", () => {
    test("POST /api/v1/reports/generate requires job_id", async ({ request }) => {
      const res = await request.post(`${getEngineBase()}/api/v1/reports/generate`, {
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        data: { job_id: "nonexistent-job", format: "html" },
      });
      expect([400, 404, 422]).toContain(res.status());
    });
  });

  // ---- AI ----
  test.describe("AI Features", () => {
    test("GET /api/v1/ai/config returns AI configuration", async ({ request }) => {
      const res = await request.get(`${getEngineBase()}/api/v1/ai/config`, {
        headers: authHeaders(),
      });
      expect(res.status()).toBeLessThan(500);
    });

    test("GET /api/v1/ai/credits returns credit balance", async ({ request }) => {
      const res = await request.get(`${getEngineBase()}/api/v1/ai/credits`, {
        headers: authHeaders(),
      });
      expect(res.status()).toBeLessThan(500);
    });

    test("GET /api/v1/ai/presets lists AI presets", async ({ request }) => {
      const res = await request.get(`${getEngineBase()}/api/v1/ai/presets`, {
        headers: authHeaders(),
      });
      expect(res.status()).toBe(200);
      const body = await res.json();
      const presets = body.presets ?? body;
      expect(Array.isArray(presets)).toBe(true);
    });

    test("GET /api/v1/ai/usage returns usage stats", async ({ request }) => {
      const res = await request.get(`${getEngineBase()}/api/v1/ai/usage`, {
        headers: authHeaders(),
      });
      expect(res.status()).toBeLessThan(500);
    });
  });

  // ---- Viewer ----
  test.describe("Viewer", () => {
    test("GET /api/v1/viewer/jobs/nonexistent/pages returns 404", async ({ request }) => {
      const res = await request.get(`${getEngineBase()}/api/v1/viewer/jobs/nonexistent/pages`, {
        headers: authHeaders(),
      });
      expect([404, 400]).toContain(res.status());
    });
  });

  // ---- Custom Endpoints ----
  test.describe("Custom Endpoints", () => {
    let endpointId: string;

    test("GET /api/v1/endpoints lists endpoints", async ({ request }) => {
      const res = await request.get(`${getEngineBase()}/api/v1/endpoints`, {
        headers: authHeaders(),
      });
      expect(res.status()).toBe(200);
    });

    test("POST /api/v1/endpoints creates endpoint", async ({ request }) => {
      const res = await request.post(`${getEngineBase()}/api/v1/endpoints`, {
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        data: { name: "e2e-test-endpoint", profile_id: "lintpdf-default" },
      });
      if (res.ok()) {
        const body = await res.json();
        endpointId = body.id ?? body.endpoint_id;
      }
      expect(res.status()).toBeLessThan(500);
    });

    test("DELETE /api/v1/endpoints/:id deletes endpoint", async ({ request }) => {
      test.skip(!endpointId, "No endpoint created");

      const res = await request.delete(`${getEngineBase()}/api/v1/endpoints/${endpointId}`, {
        headers: authHeaders(),
      });
      expect([200, 204, 404]).toContain(res.status());
    });
  });

  // ---- Branding ----
  test.describe("Branding", () => {
    test("GET /api/v1/tenants/{id}/brand-profiles lists brands", async ({ request }) => {
      // Use a placeholder tenant ID — the exact one depends on test state
      const res = await request.get(`${getEngineBase()}/api/v1/tenants/test/brand-profiles`, {
        headers: authHeaders(),
      });
      // May be 404 for unknown tenant, but should not be 500
      expect(res.status()).toBeLessThan(500);
    });
  });

  // ---- Color Config ----
  test.describe("Color Config", () => {
    test("GET /api/v1/tenants/{id}/color-config returns config", async ({ request }) => {
      const res = await request.get(`${getEngineBase()}/api/v1/tenants/test/color-config`, {
        headers: authHeaders(),
      });
      expect(res.status()).toBeLessThan(500);
    });
  });
});

// ---- Admin Routes ----
test.describe("Engine Direct API — Admin Routes", () => {
  const adminKey = () => getAdminApiKey();
  const adminHeaders = () => ({ "X-Admin-Key": adminKey() });

  test.beforeAll(async () => {
    test.skip(!adminKey(), "No admin API key available");
  });

  test("GET /api/v1/admin/tenants lists all tenants", async ({ request }) => {
    const res = await request.get(`${getEngineBase()}/api/v1/admin/tenants`, {
      headers: adminHeaders(),
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body.tenants ?? body)).toBe(true);
  });

  test("GET /api/v1/admin/jobs lists all jobs", async ({ request }) => {
    const res = await request.get(`${getEngineBase()}/api/v1/admin/jobs`, {
      headers: adminHeaders(),
    });
    expect(res.status()).toBe(200);
  });

  test("GET /api/v1/admin/trials lists trial submissions", async ({ request }) => {
    const res = await request.get(`${getEngineBase()}/api/v1/admin/trials`, {
      headers: adminHeaders(),
    });
    expect(res.status()).toBe(200);
  });

  test("GET /api/v1/admin/ai/usage returns system AI usage", async ({ request }) => {
    const res = await request.get(`${getEngineBase()}/api/v1/admin/ai/usage`, {
      headers: adminHeaders(),
    });
    expect(res.status()).toBeLessThan(500);
  });

  test("wrong admin key returns 401", async ({ request }) => {
    const res = await request.get(`${getEngineBase()}/api/v1/admin/tenants`, {
      headers: { "X-Admin-Key": "wrong-key-12345" },
    });
    expect(res.status()).toBe(401);
  });

  test("missing admin key returns 401", async ({ request }) => {
    const res = await request.get(`${getEngineBase()}/api/v1/admin/tenants`);
    expect(res.status()).toBe(401);
  });
});

// ---- Unauthenticated access ----
test.describe("Engine Direct API — Unauthenticated", () => {
  test("GET /api/v1/jobs without API key returns 401", async ({ request }) => {
    const res = await request.get(`${getEngineBase()}/api/v1/jobs`);
    expect(res.status()).toBe(401);
  });

  test("POST /api/v1/jobs without API key returns 401", async ({ request }) => {
    const res = await request.post(`${getEngineBase()}/api/v1/jobs`);
    expect(res.status()).toBe(401);
  });

  test("invalid API key returns 401", async ({ request }) => {
    const res = await request.get(`${getEngineBase()}/api/v1/jobs`, {
      headers: { Authorization: "Bearer invalid-key-12345" },
    });
    expect(res.status()).toBe(401);
  });
});
