import { test, expect } from "@playwright/test";
import { getAdminKey, getTenant } from "../helpers";

test.describe("Admin API", () => {
  let adminKey: string;

  test.beforeAll(() => {
    adminKey = getAdminKey();
  });

  // ── Tenant Management ──

  test("GET /api/v1/admin/tenants lists all tenants", async ({ request }) => {
    test.skip(!adminKey, "No admin key");

    const res = await request.get("/api/v1/admin/tenants", {
      headers: { "X-Admin-Key": adminKey },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("tenants");
    expect(body).toHaveProperty("total");
    expect(body).toHaveProperty("page");
    expect(Array.isArray(body.tenants)).toBe(true);
    expect(body.total).toBeGreaterThanOrEqual(1);
  });

  test("GET /api/v1/admin/tenants/:id returns tenant detail", async ({
    request,
  }) => {
    const tenant = getTenant("free");
    test.skip(!adminKey || !tenant, "No admin key or tenant");

    const res = await request.get(`/api/v1/admin/tenants/${tenant?.id}`, {
      headers: { "X-Admin-Key": adminKey },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.id).toBe(tenant?.id);
    expect(body).toHaveProperty("plan");
    expect(body).toHaveProperty("rate_limit_daily");
    expect(body).toHaveProperty("is_active");
  });

  test("GET /api/v1/admin/tenants/:id returns 404 for unknown tenant", async ({
    request,
  }) => {
    test.skip(!adminKey, "No admin key");

    const res = await request.get(
      "/api/v1/admin/tenants/00000000-0000-0000-0000-000000000000",
      { headers: { "X-Admin-Key": adminKey } },
    );
    expect(res.status()).toBe(404);
  });

  // ── Plan Management ──

  test("PATCH /api/v1/admin/tenants/:id/plan updates plan", async ({
    request,
  }) => {
    const tenant = getTenant("free");
    test.skip(!adminKey || !tenant, "No admin key or tenant");

    // Upgrade to starter
    const res = await request.patch(
      `/api/v1/admin/tenants/${tenant?.id}/plan`,
      {
        headers: {
          "X-Admin-Key": adminKey,
          "Content-Type": "application/json",
        },
        data: { plan: "starter" },
      },
    );
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.updated).toBe(true);

    // Revert to free
    await request.patch(`/api/v1/admin/tenants/${tenant?.id}/plan`, {
      headers: { "X-Admin-Key": adminKey, "Content-Type": "application/json" },
      data: { plan: "free" },
    });
  });

  // ── Stripe Sync ──

  test("PATCH /api/v1/admin/tenants/:id/stripe sets Stripe IDs", async ({
    request,
  }) => {
    const tenant = getTenant("starter");
    test.skip(!adminKey || !tenant, "No admin key or tenant");

    const res = await request.patch(
      `/api/v1/admin/tenants/${tenant?.id}/stripe`,
      {
        headers: {
          "X-Admin-Key": adminKey,
          "Content-Type": "application/json",
        },
        data: {
          stripe_customer_id: "cus_test_123",
          stripe_subscription_item_id: "si_test_456",
        },
      },
    );
    expect(res.status()).toBe(200);

    // Verify
    const detail = await request.get(`/api/v1/admin/tenants/${tenant?.id}`, {
      headers: { "X-Admin-Key": adminKey },
    });
    const detailBody = await detail.json();
    expect(detailBody.stripe_customer_id).toBe("cus_test_123");
  });

  // ── Tenant Status ──

  test("PATCH /api/v1/admin/tenants/:id/status toggles active state", async ({
    request,
  }) => {
    const tenant = getTenant("enterprise");
    test.skip(!adminKey || !tenant, "No admin key or tenant");

    // Suspend
    const res = await request.patch(
      `/api/v1/admin/tenants/${tenant?.id}/status`,
      {
        headers: {
          "X-Admin-Key": adminKey,
          "Content-Type": "application/json",
        },
        data: { is_active: false },
      },
    );
    expect(res.status()).toBe(200);

    // Reactivate
    await request.patch(`/api/v1/admin/tenants/${tenant?.id}/status`, {
      headers: { "X-Admin-Key": adminKey, "Content-Type": "application/json" },
      data: { is_active: true },
    });
  });

  // ── API Key Management ──

  test("POST + GET + DELETE api keys for tenant", async ({ request }) => {
    const tenant = getTenant("growth");
    test.skip(!adminKey || !tenant, "No admin key or tenant");

    // Create
    const createRes = await request.post(
      `/api/v1/admin/tenants/${tenant?.id}/keys`,
      {
        headers: {
          "X-Admin-Key": adminKey,
          "Content-Type": "application/json",
        },
        data: { label: "playwright-test-key" },
      },
    );
    expect(createRes.status()).toBe(201);
    const created = await createRes.json();
    expect(created).toHaveProperty("raw_key");
    expect(created.raw_key.startsWith("grd_")).toBe(true);
    expect(created.label).toBe("playwright-test-key");

    // List
    const listRes = await request.get(
      `/api/v1/admin/tenants/${tenant?.id}/keys`,
      { headers: { "X-Admin-Key": adminKey } },
    );
    expect(listRes.status()).toBe(200);
    const listBody = await listRes.json();
    expect(listBody.keys.length).toBeGreaterThanOrEqual(1);

    // Revoke
    const revokeRes = await request.delete(
      `/api/v1/admin/tenants/${tenant?.id}/keys/${created.id}`,
      { headers: { "X-Admin-Key": adminKey } },
    );
    expect(revokeRes.status()).toBe(204);
  });

  // ── Cross-Tenant Jobs ──

  test("GET /api/v1/admin/jobs lists jobs across tenants", async ({
    request,
  }) => {
    test.skip(!adminKey, "No admin key");

    const res = await request.get("/api/v1/admin/jobs", {
      headers: { "X-Admin-Key": adminKey },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("jobs");
    expect(body).toHaveProperty("total");
    expect(Array.isArray(body.jobs)).toBe(true);
  });

  // ── Auth Errors ──

  test("no admin key returns 401", async ({ request }) => {
    const res = await request.get("/api/v1/admin/tenants");
    expect(res.status()).toBe(401);
  });

  test("wrong admin key returns 401", async ({ request }) => {
    const res = await request.get("/api/v1/admin/tenants", {
      headers: { "X-Admin-Key": "totally-wrong-key" },
    });
    expect(res.status()).toBe(401);
  });
});
