import { test, expect } from "@playwright/test";

test.describe("Health & Status Endpoints", () => {
  test("GET /health returns ok", async ({ request }) => {
    const res = await request.get("/health");
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.status).toBe("ok");
    expect(body.service).toBe("lintpdf");
  });

  test("GET /api/v1/status returns service details", async ({ request }) => {
    const res = await request.get("/api/v1/status");
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.status).toBe("ok");
    expect(body.database).toBe("connected");
    expect(body.redis).toBe("connected");
    expect(body).toHaveProperty("queue_depth");
    expect(body).toHaveProperty("worker_count");
  });

  test("GET /api/v1/beta/status returns beta mode flag", async ({ request }) => {
    const res = await request.get("/api/v1/beta/status");
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("beta_mode");
    expect(typeof body.beta_mode).toBe("boolean");
  });

  test("GET /docs returns Swagger UI", async ({ request }) => {
    const res = await request.get("/docs");
    expect(res.status()).toBe(200);
  });

  test("GET /redoc returns ReDoc", async ({ request }) => {
    const res = await request.get("/redoc");
    expect(res.status()).toBe(200);
  });
});
