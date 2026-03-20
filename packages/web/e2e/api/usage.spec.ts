import { test, expect } from "@playwright/test";
import { getAnyTenantKey } from "../helpers";

test.describe("Usage Tracking", () => {
  test("GET /api/v1/usage returns daily usage info", async ({ request }) => {
    const apiKey = getAnyTenantKey();
    test.skip(!apiKey, "No test credentials");

    const res = await request.get("/api/v1/usage", {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("plan");
    expect(body).toHaveProperty("limit");
    expect(body).toHaveProperty("used");
    expect(body).toHaveProperty("remaining_included");
    expect(typeof body.limit).toBe("number");
    expect(typeof body.used).toBe("number");
  });

  test("usage requires authentication", async ({ request }) => {
    const res = await request.get("/api/v1/usage");
    expect(res.status()).toBe(401);
  });
});
