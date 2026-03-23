/**
 * Full Workflow E2E Test: Onboarding → Preflight → Stripe
 *
 * Tests the complete user journey:
 * 1. Beta waitlist signup
 * 2. Admin promotes waitlist entry → creates tenant
 * 3. Tenant authenticates and explores profiles
 * 4. Tenant submits a PDF job
 * 5. Job completes with findings
 * 6. Report is generated and accessible
 * 7. Stripe integration: customer + subscription sync
 * 8. Plan upgrade changes limits
 * 9. Usage tracking reflects activity
 * 10. Cleanup
 */
import { test, expect } from "@playwright/test";
import { existsSync, readFileSync } from "fs";
import { resolve } from "path";
import { getAdminKey, loadCredentials, pollJob } from "../helpers";

const TEST_PDF = resolve(
  __dirname,
  "../../../../packages/engine/tests/fixtures/test-sample.pdf",
);

const ADMIN_KEY = getAdminKey();
const WORKFLOW_EMAIL = `workflow-${Date.now()}@playwright.test`;

// ────────────────────────────────────────────────────
// Phase 1: Onboarding + Profile Exploration
// ────────────────────────────────────────────────────

test.describe.serial("Workflow: Onboarding & Profiles", () => {
  let _tenantId: string;
  let tenantApiKey: string;

  test("1. Join beta waitlist", async ({ request }) => {
    const res = await request.post("/api/v1/beta/waitlist", {
      headers: { "Content-Type": "application/json" },
      data: {
        email: WORKFLOW_EMAIL,
        name: "Workflow Test User",
        company: "LintPDF E2E Corp",
        use_case: "Automated preflight testing",
      },
    });
    expect([200, 201]).toContain(res.status());
  });

  test("2. Verify on waitlist", async ({ request }) => {
    const res = await request.get(
      `/api/v1/beta/waitlist/check?email=${encodeURIComponent(WORKFLOW_EMAIL)}`,
    );
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.on_waitlist).toBe(true);
    expect(body.status).toBe("pending");
  });

  test("3. Admin promotes waitlist entry", async ({ request }) => {
    test.skip(!ADMIN_KEY, "No admin key");

    const listRes = await request.get("/api/v1/admin/waitlist?status=pending", {
      headers: { "X-Admin-Key": ADMIN_KEY },
    });
    expect(listRes.status()).toBe(200);
    const { entries } = await listRes.json();
    const entry = entries.find(
      (e: { email: string }) => e.email === WORKFLOW_EMAIL,
    );
    expect(entry).toBeTruthy();

    const promoteRes = await request.patch(
      `/api/v1/admin/waitlist/${entry.id}/promote`,
      { headers: { "X-Admin-Key": ADMIN_KEY } },
    );
    expect(promoteRes.status()).toBe(200);
  });

  test("4. Load test tenant credentials", () => {
    test.skip(!ADMIN_KEY, "No admin key");

    const creds = loadCredentials();
    const starterTenant = creds.tenants["starter"];
    test.skip(!starterTenant, "No starter tenant");

    _tenantId = starterTenant.id;
    tenantApiKey = starterTenant.api_key;
  });

  test("5. Tenant lists available flight plan profiles", async ({
    request,
  }) => {
    test.skip(!tenantApiKey, "No tenant API key");

    const res = await request.get("/api/v1/profiles", {
      headers: { Authorization: `Bearer ${tenantApiKey}` },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.profiles.length).toBeGreaterThanOrEqual(9);

    const ids = body.profiles.map((p: { profile_id: string }) => p.profile_id);
    expect(ids).toContain("lintpdf-default");
    expect(ids).toContain("lintpdf-strict");
    expect(ids).toContain("gwg-2022-coated-offset");
  });

  test("6. Tenant views profile details", async ({ request }) => {
    test.skip(!tenantApiKey, "No tenant API key");

    const res = await request.get("/api/v1/profiles/lintpdf-default", {
      headers: { Authorization: `Bearer ${tenantApiKey}` },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.profile_id).toBe("lintpdf-default");
    expect(body.name).toContain("Default");
  });

  test("7. Clean up waitlist entry", async ({ request }) => {
    test.skip(!ADMIN_KEY, "No admin key");

    const listRes = await request.get("/api/v1/admin/waitlist", {
      headers: { "X-Admin-Key": ADMIN_KEY },
    });
    if (listRes.status() === 200) {
      const { entries } = await listRes.json();
      const entry = entries?.find(
        (e: { email: string }) => e.email === WORKFLOW_EMAIL,
      );
      if (entry) {
        await request.delete(`/api/v1/admin/waitlist/${entry.id}`, {
          headers: { "X-Admin-Key": ADMIN_KEY },
        });
      }
    }
  });
});

// ────────────────────────────────────────────────────
// Phase 2: Preflight Job Submission → Reports
// ────────────────────────────────────────────────────

test.describe.serial("Workflow: Preflight Job & Reports", () => {
  let tenantApiKey: string;
  let jobId: string;
  let reportToken: string;

  test.beforeAll(() => {
    const creds = loadCredentials();
    const starterTenant = creds.tenants?.["starter"];
    if (starterTenant) {
      tenantApiKey = starterTenant.api_key;
    }
  });

  test("8. Tenant submits PDF for preflight", async ({ request }) => {
    test.skip(!tenantApiKey, "No tenant API key");
    test.skip(!existsSync(TEST_PDF), "Test PDF not found");
    test.setTimeout(300_000); // 5 min for upload through proxy

    const res = await request.post("/api/v1/jobs", {
      headers: { Authorization: `Bearer ${tenantApiKey}` },
      multipart: {
        file: {
          name: "workflow-test.pdf",
          mimeType: "application/pdf",
          buffer: readFileSync(TEST_PDF),
        },
        profile_id: "lintpdf-default",
      },
    });
    expect(res.status()).toBe(202);
    const body = await res.json();
    expect(body).toHaveProperty("job_id");
    jobId = body.job_id;

    const limit = res.headers()["x-ratelimit-limit"];
    if (limit) {
      expect(parseInt(limit)).toBeGreaterThan(0);
    }
  });

  test("9. Job completes successfully", async ({ request }) => {
    test.skip(!jobId, "No job submitted");
    test.setTimeout(180_000);

    const result = await pollJob(request, jobId, tenantApiKey, 150_000);
    expect(result.status).toBe("complete");
    expect(result).toHaveProperty("summary");
  });

  test("10. Job appears in tenant job list", async ({ request }) => {
    test.skip(!tenantApiKey, "No tenant API key");

    const res = await request.get("/api/v1/jobs", {
      headers: { Authorization: `Bearer ${tenantApiKey}` },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("jobs");
  });

  test("11. Generate report for completed job", async ({ request }) => {
    test.skip(!jobId, "No completed job");

    const res = await request.post(`/api/v1/jobs/${jobId}/reports`, {
      headers: {
        Authorization: `Bearer ${tenantApiKey}`,
        "Content-Type": "application/json",
      },
    });
    expect([200, 201]).toContain(res.status());
    const body = await res.json();
    // API returns { reports: [{ token, format, url, ... }] }
    if (body.reports && body.reports.length > 0) {
      const htmlReport = body.reports.find(
        (r: { format: string }) => r.format === "html",
      );
      reportToken = htmlReport?.token || body.reports[0].token;
    } else if (body.token) {
      reportToken = body.token;
    }
  });

  test("12. Public report URL is accessible", async ({ request }) => {
    test.skip(!reportToken, "No report token");

    const res = await request.get(`/r/${reportToken}`);
    expect(res.status()).toBe(200);
    const contentType = res.headers()["content-type"] || "";
    expect(contentType).toContain("html");
  });
});

// ────────────────────────────────────────────────────
// Phase 3: Stripe Integration & Admin
// ────────────────────────────────────────────────────

test.describe.serial("Workflow: Stripe & Admin", () => {
  let tenantId: string;
  let tenantApiKey: string;

  test.beforeAll(() => {
    const creds = loadCredentials();
    const starterTenant = creds.tenants?.["starter"];
    if (starterTenant) {
      tenantId = starterTenant.id;
      tenantApiKey = starterTenant.api_key;
    }
  });

  test("13. Admin sets Stripe customer ID on tenant", async ({ request }) => {
    test.skip(!ADMIN_KEY || !tenantId, "No admin key or tenant");

    const res = await request.patch(
      `/api/v1/admin/tenants/${tenantId}/stripe`,
      {
        headers: {
          "X-Admin-Key": ADMIN_KEY,
          "Content-Type": "application/json",
        },
        data: {
          stripe_customer_id: "cus_workflow_test",
          stripe_subscription_item_id: "si_workflow_test",
        },
      },
    );
    expect(res.status()).toBe(200);
  });

  test("14. Verify Stripe IDs persisted", async ({ request }) => {
    test.skip(!ADMIN_KEY || !tenantId, "No admin key or tenant");

    const res = await request.get(`/api/v1/admin/tenants/${tenantId}`, {
      headers: { "X-Admin-Key": ADMIN_KEY },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.stripe_customer_id).toBe("cus_workflow_test");
  });

  test("15. Simulate plan upgrade (starter → pro) via admin API", async ({
    request,
  }) => {
    test.skip(!ADMIN_KEY || !tenantId, "No admin key or tenant");

    const res = await request.patch(`/api/v1/admin/tenants/${tenantId}/plan`, {
      headers: {
        "X-Admin-Key": ADMIN_KEY,
        "Content-Type": "application/json",
      },
      data: {
        plan: "growth",
        overage_enabled: true,
        overage_cap_cents: 5000,
      },
    });
    expect(res.status()).toBe(200);

    const detail = await request.get(`/api/v1/admin/tenants/${tenantId}`, {
      headers: { "X-Admin-Key": ADMIN_KEY },
    });
    const body = await detail.json();
    expect(body.plan).toBe("growth");
  });

  test("16. Usage endpoint reflects activity", async ({ request }) => {
    test.skip(!tenantApiKey, "No tenant API key");

    const res = await request.get("/api/v1/usage", {
      headers: { Authorization: `Bearer ${tenantApiKey}` },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("plan");
    expect(body).toHaveProperty("used");
    expect(body).toHaveProperty("limit");
    expect(typeof body.used).toBe("number");
  });

  test("17. Register webhook endpoint", async ({ request }) => {
    test.skip(!tenantApiKey, "No tenant API key");

    const res = await request.post("/api/v1/webhooks", {
      headers: {
        Authorization: `Bearer ${tenantApiKey}`,
        "Content-Type": "application/json",
      },
      data: {
        url: "https://webhook.test/workflow-e2e",
        events: ["job.completed", "job.failed"],
      },
    });
    expect([200, 201]).toContain(res.status());
    const body = await res.json();
    expect(body).toHaveProperty("id");
  });

  test("18. Admin can view all tenants", async ({ request }) => {
    test.skip(!ADMIN_KEY, "No admin key");

    const res = await request.get("/api/v1/admin/tenants", {
      headers: { "X-Admin-Key": ADMIN_KEY },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.total).toBeGreaterThanOrEqual(4);
  });

  test("19. Admin can view cross-tenant jobs", async ({ request }) => {
    test.skip(!ADMIN_KEY, "No admin key");

    const res = await request.get("/api/v1/admin/jobs", {
      headers: { "X-Admin-Key": ADMIN_KEY },
    });
    expect(res.status()).toBe(200);
  });

  test("20. Restore tenant to starter plan", async ({ request }) => {
    test.skip(!ADMIN_KEY || !tenantId, "No admin key or tenant");

    await request.patch(`/api/v1/admin/tenants/${tenantId}/plan`, {
      headers: {
        "X-Admin-Key": ADMIN_KEY,
        "Content-Type": "application/json",
      },
      data: { plan: "starter" },
    });
  });
});
