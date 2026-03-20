import { test, expect } from "@playwright/test";
import { getAnyTenantKey, getAdminKey } from "../helpers";

test.describe("Authentication", () => {
  test("missing API key returns 401", async ({ request }) => {
    const res = await request.get("/api/v1/jobs");
    expect(res.status()).toBe(401);
    const body = await res.json();
    expect(body.detail).toContain("Missing API key");
  });

  test("invalid API key returns 401", async ({ request }) => {
    const res = await request.get("/api/v1/jobs", {
      headers: { Authorization: "Bearer lpdf_invalid_key_12345" },
    });
    expect(res.status()).toBe(401);
    const body = await res.json();
    expect(body.detail).toContain("Invalid API key");
  });

  test("valid API key returns 200 on protected endpoint", async ({ request }) => {
    const apiKey = getAnyTenantKey();
    test.skip(!apiKey, "No test credentials available");

    const res = await request.get("/api/v1/jobs", {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    expect(res.status()).toBe(200);
  });

  test("wrong admin key returns 401", async ({ request }) => {
    const res = await request.get("/api/v1/admin/tenants", {
      headers: { "X-Admin-Key": "wrong-admin-key" },
    });
    expect(res.status()).toBe(401);
  });

  test("valid admin key returns 200 on admin endpoint", async ({ request }) => {
    const adminKey = getAdminKey();
    test.skip(!adminKey, "No admin key available");

    const res = await request.get("/api/v1/admin/tenants", {
      headers: { "X-Admin-Key": adminKey },
    });
    expect(res.status()).toBe(200);
  });
});
