import { test, expect } from "@playwright/test";
import { getAnyTenantKey } from "../helpers";

test.describe("Flight Plan Profiles", () => {
  test("GET /api/v1/profiles lists built-in profiles", async ({ request }) => {
    const key = getAnyTenantKey();
    test.skip(!key, "No test tenant key available");

    const res = await request.get("/api/v1/profiles", {
      headers: { Authorization: `Bearer ${key}` },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body.profiles)).toBe(true);
    expect(body.profiles.length).toBeGreaterThanOrEqual(9);

    // Check expected profile IDs
    const ids = body.profiles.map((p: { profile_id: string }) => p.profile_id);
    expect(ids).toContain("lintpdf-default");
    expect(ids).toContain("lintpdf-strict");
    expect(ids).toContain("gwg-2022-coated-offset");
  });

  test("GET /api/v1/profiles/:id returns profile detail", async ({
    request,
  }) => {
    const key = getAnyTenantKey();
    test.skip(!key, "No test tenant key available");

    const res = await request.get("/api/v1/profiles/lintpdf-default", {
      headers: { Authorization: `Bearer ${key}` },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.profile_id).toBe("lintpdf-default");
    expect(body).toHaveProperty("name");
  });

  test("GET /api/v1/profiles/:id returns 404 for unknown profile", async ({
    request,
  }) => {
    const key = getAnyTenantKey();
    test.skip(!key, "No test tenant key available");

    const res = await request.get("/api/v1/profiles/nonexistent-profile", {
      headers: { Authorization: `Bearer ${key}` },
    });
    expect(res.status()).toBe(404);
  });
});
