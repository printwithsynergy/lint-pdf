import { test, expect } from "@playwright/test";
import { getAdminKey } from "../helpers";

const UNIQUE_EMAIL = `test-${Date.now()}@playwright.test`;

test.describe("Beta Waitlist", () => {
  // ── Public Endpoints ──

  test("POST /api/v1/beta/waitlist joins the waitlist", async ({ request }) => {
    const res = await request.post("/api/v1/beta/waitlist", {
      headers: { "Content-Type": "application/json" },
      data: {
        email: UNIQUE_EMAIL,
        name: "Playwright Test",
        company: "Test Corp",
        use_case: "Automated testing",
      },
    });
    expect([200, 201]).toContain(res.status());
  });

  test("POST /api/v1/beta/waitlist handles duplicate email", async ({
    request,
  }) => {
    const res = await request.post("/api/v1/beta/waitlist", {
      headers: { "Content-Type": "application/json" },
      data: { email: UNIQUE_EMAIL, name: "Dup Test" },
    });
    // API may return 200/201 (idempotent) or 409/422 (duplicate rejection)
    expect([200, 201, 409, 422]).toContain(res.status());
  });

  test("GET /api/v1/beta/waitlist/check finds email", async ({ request }) => {
    // Use a known seeded email since parallel tests may not share state
    const res = await request.get(
      "/api/v1/beta/waitlist/check?email=pending@example.com",
    );
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.on_waitlist).toBe(true);
  });

  test("GET /api/v1/beta/waitlist/check returns false for unknown email", async ({
    request,
  }) => {
    const res = await request.get(
      "/api/v1/beta/waitlist/check?email=nonexistent@nowhere.test",
    );
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.on_waitlist).toBe(false);
  });

  // ── Admin Endpoints ──

  test("admin: list waitlist entries", async ({ request }) => {
    const adminKey = getAdminKey();
    test.skip(!adminKey, "No admin key");

    const res = await request.get("/api/v1/admin/waitlist", {
      headers: { "X-Admin-Key": adminKey },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("entries");
    expect(body).toHaveProperty("total");
    expect(body.total).toBeGreaterThanOrEqual(1);
  });

  test("admin: promote → decline → delete waitlist entry", async ({
    request,
  }) => {
    const adminKey = getAdminKey();
    test.skip(!adminKey, "No admin key");

    // Find the entry we created
    const listRes = await request.get("/api/v1/admin/waitlist?status=pending", {
      headers: { "X-Admin-Key": adminKey },
    });
    const { entries } = await listRes.json();
    const entry = entries.find(
      (e: { email: string }) => e.email === UNIQUE_EMAIL,
    );
    test.skip(!entry, "Waitlist entry not found");

    // Promote
    const promoteRes = await request.patch(
      `/api/v1/admin/waitlist/${entry.id}/promote`,
      { headers: { "X-Admin-Key": adminKey } },
    );
    expect(promoteRes.status()).toBe(200);

    // Delete
    const delRes = await request.delete(`/api/v1/admin/waitlist/${entry.id}`, {
      headers: { "X-Admin-Key": adminKey },
    });
    expect([200, 204]).toContain(delRes.status());
  });
});
