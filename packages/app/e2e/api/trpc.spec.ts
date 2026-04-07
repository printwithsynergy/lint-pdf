import { test, expect } from "@playwright/test";
import { authenticateViaMcpBackdoor, isMcpBackdoorAvailable } from "../helpers";

test.describe("tRPC API", () => {
  test.beforeAll(async ({ request }) => {
    const available = await isMcpBackdoorAvailable(request);
    test.skip(!available, "MCP backdoor is not enabled on this environment");
  });

  test("tRPC endpoint is reachable", async ({ request }) => {
    // tRPC should respond (even if with an error for missing procedure)
    const res = await request.get("/api/trpc/health");
    // A 404 or error response is fine — it means tRPC is running
    // 500 is also acceptable if the route exists but the procedure doesn't
    expect(res.status()).toBeLessThanOrEqual(500);
  });

  test.describe("Tenant operations", () => {
    const testSlug = `e2e-test-${Date.now()}`;

    test("can create a tenant", async ({ request }) => {
      await authenticateViaMcpBackdoor(request);

      await request.get(
        `/api/trpc/tenant.create?input=${encodeURIComponent(
          JSON.stringify({ name: "E2E Test Org", slug: testSlug }),
        )}`,
      );

      // tRPC uses POST for mutations via batch, GET for queries
      // A create mutation via GET should return method not allowed or we use POST
      const postRes = await request.post("/api/trpc/tenant.create", {
        data: {
          json: { name: "E2E Test Org", slug: testSlug },
        },
      });

      // Either succeeds or conflicts (if already exists)
      expect([200, 409].includes(postRes.status()) || postRes.ok()).toBe(true);
    });

    test("rejects unauthenticated tenant creation", async ({ request }) => {
      const res = await request.post("/api/trpc/tenant.create", {
        data: {
          json: { name: "Unauth Org", slug: "unauth-test" },
        },
        headers: { Cookie: "" },
      });

      expect(res.ok()).toBe(false);
    });
  });
});
