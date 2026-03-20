import { test, expect } from "@playwright/test";
import { getAnyTenantKey } from "../helpers";

test.describe("Webhook Management", () => {
  let apiKey: string;
  let webhookId: string;

  test.beforeAll(() => {
    apiKey = getAnyTenantKey();
  });

  test("POST /api/v1/webhooks registers an endpoint", async ({ request }) => {
    test.skip(!apiKey, "No test credentials");

    const res = await request.post("/api/v1/webhooks", {
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      data: {
        url: "https://webhook.test/grounded",
        events: ["job.completed", "job.failed"],
      },
    });
    expect([200, 201]).toContain(res.status());
    const body = await res.json();
    expect(body).toHaveProperty("id");
    expect(body.url).toBe("https://webhook.test/grounded");
    webhookId = body.id;
  });

  test("GET /api/v1/webhooks lists endpoints", async ({ request }) => {
    test.skip(!apiKey, "No test credentials");

    const res = await request.get("/api/v1/webhooks", {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("webhooks");
    expect(Array.isArray(body.webhooks)).toBe(true);
  });

  test("PATCH /api/v1/webhooks/:id updates endpoint", async ({ request }) => {
    test.skip(!apiKey || !webhookId, "No webhook to update");

    const res = await request.patch(`/api/v1/webhooks/${webhookId}`, {
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      data: { url: "https://webhook.test/grounded-updated" },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.url).toBe("https://webhook.test/grounded-updated");
  });

  test("DELETE /api/v1/webhooks/:id removes endpoint", async ({ request }) => {
    test.skip(!apiKey || !webhookId, "No webhook to delete");

    const res = await request.delete(`/api/v1/webhooks/${webhookId}`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    expect([200, 204]).toContain(res.status());
  });
});
