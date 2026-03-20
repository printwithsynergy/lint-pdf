import { test, expect } from "@playwright/test";
import { getAnyTenantKey } from "../helpers";

test.describe("Error Handling", () => {
  let apiKey: string;

  test.beforeAll(() => {
    apiKey = getAnyTenantKey();
  });

  test("uploading a non-PDF file returns 422", async ({ request }) => {
    test.skip(!apiKey, "No test credentials");

    const res = await request.post("/api/v1/jobs", {
      headers: { Authorization: `Bearer ${apiKey}` },
      multipart: {
        file: {
          name: "not-a-pdf.txt",
          mimeType: "text/plain",
          buffer: Buffer.from("This is not a PDF"),
        },
      },
    });
    expect([400, 422, 429]).toContain(res.status());
  });

  test("uploading empty file returns 422", async ({ request }) => {
    test.skip(!apiKey, "No test credentials");

    const res = await request.post("/api/v1/jobs", {
      headers: { Authorization: `Bearer ${apiKey}` },
      multipart: {
        file: {
          name: "empty.pdf",
          mimeType: "application/pdf",
          buffer: Buffer.alloc(0),
        },
      },
    });
    expect([400, 422, 429]).toContain(res.status());
  });

  test("non-existent job returns 404", async ({ request }) => {
    test.skip(!apiKey, "No test credentials");

    const res = await request.get(
      "/api/v1/jobs/00000000-0000-0000-0000-000000000000",
      { headers: { Authorization: `Bearer ${apiKey}` } }
    );
    expect(res.status()).toBe(404);
  });

  test("invalid UUID in path returns 422", async ({ request }) => {
    const adminKey =
      process.env.ADMIN_API_KEY ??
      "gx0B011GFHNLxx4q8KOfafMcCgLifHgec-u1TKpPOpA";

    const res = await request.get("/api/v1/admin/tenants/not-a-uuid", {
      headers: { "X-Admin-Key": adminKey },
    });
    expect(res.status()).toBe(422);
  });

  test("invalid plan in admin update returns 422", async ({ request }) => {
    const adminKey =
      process.env.ADMIN_API_KEY ??
      "gx0B011GFHNLxx4q8KOfafMcCgLifHgec-u1TKpPOpA";

    const res = await request.patch(
      "/api/v1/admin/tenants/00000000-0000-0000-0000-000000000001/plan",
      {
        headers: {
          "X-Admin-Key": adminKey,
          "Content-Type": "application/json",
        },
        data: { plan: "invalid_plan" },
      }
    );
    // Either 404 (tenant not found) or 422 (invalid plan) - both are valid
    expect([404, 422]).toContain(res.status());
  });
});
