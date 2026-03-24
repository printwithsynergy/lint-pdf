import { test, expect } from "@playwright/test";

test.describe("Webhook Endpoints", () => {
  test.describe("LintPDF Engine Webhooks", () => {
    test("rejects requests without valid signature", async ({ request }) => {
      const res = await request.post("/api/lintpdf/webhooks", {
        data: { event: "job.completed", jobId: "test-123" },
        headers: { "Content-Type": "application/json" },
      });

      // Should reject — no valid webhook signature
      expect(res.ok()).toBe(false);
      expect(res.status()).toBeGreaterThanOrEqual(400);
    });

    test("rejects empty body", async ({ request }) => {
      const res = await request.post("/api/lintpdf/webhooks", {
        headers: { "Content-Type": "application/json" },
      });

      expect(res.ok()).toBe(false);
    });
  });

  test.describe("Stripe Webhooks", () => {
    test("rejects requests without Stripe signature", async ({ request }) => {
      const res = await request.post("/api/stripe/webhooks", {
        data: { type: "checkout.session.completed" },
        headers: { "Content-Type": "application/json" },
      });

      // Should reject — no valid Stripe signature header
      expect(res.ok()).toBe(false);
      expect(res.status()).toBeGreaterThanOrEqual(400);
    });
  });
});
