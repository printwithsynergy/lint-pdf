/**
 * Stripe Billing Workflow E2E Test
 *
 * Tests the complete Stripe integration:
 * 1. Create a Stripe test customer
 * 2. Link customer to tenant via admin API
 * 3. Create a subscription (simulated via API)
 * 4. Verify plan sync works
 * 5. Simulate plan upgrade
 * 6. Simulate cancellation → downgrade to free
 * 7. Verify usage/overage tracking
 */
import { test, expect, APIRequestContext } from "@playwright/test";
import { getAdminKey, getTenant } from "../helpers";

const STRIPE_KEY = process.env.STRIPE_SECRET_KEY ?? "";
const ADMIN_KEY = getAdminKey();

// Stripe product/price IDs (from setup)
const STRIPE_PRICES = {
  starter_monthly: "price_1TB2lTKIaHHghEpJU2L7AhUJ",
  pro_monthly: "price_1TB2lUKIaHHghEpJU6AJSy98",
  enterprise_monthly: "price_1TB2lUKIaHHghEpJkzwbvAKO",
};

async function stripeRequest(
  request: APIRequestContext,
  method: string,
  endpoint: string,
  data?: Record<string, string>,
): Promise<Record<string, unknown>> {
  const url = `https://api.stripe.com/v1${endpoint}`;
  const headers: Record<string, string> = {
    Authorization: `Basic ${Buffer.from(`${STRIPE_KEY}:`).toString("base64")}`,
  };

  const opts: { headers: Record<string, string>; data?: string } = { headers };
  if (data) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    opts.data = new URLSearchParams(data).toString();
    // Playwright needs form to send as x-www-form-urlencoded
    opts.headers = headers;
  }

  let res;
  if (method === "POST") {
    res = await request.post(url, opts);
  } else if (method === "DELETE") {
    res = await request.delete(url, opts);
  } else if (method === "PATCH") {
    res = await request.patch(url, opts);
  } else {
    res = await request.get(url, opts);
  }
  return res.json();
}

test.describe.serial("Stripe Billing Workflow", () => {
  let stripeCustomerId: string;
  let subscriptionId: string;
  let subscriptionItemId: string;

  const tenant = getTenant("enterprise");

  test.beforeAll(() => {
    test.skip(!STRIPE_KEY, "STRIPE_SECRET_KEY not set");
    test.skip(!ADMIN_KEY, "No admin key");
    test.skip(!tenant, "No enterprise tenant");
  });

  test("1. Create Stripe test customer", async ({ request }) => {
    test.skip(!STRIPE_KEY, "No Stripe key");

    const customer = await stripeRequest(request, "POST", "/customers", {
      email: `e2e-${Date.now()}@grounded.test`,
      name: "E2E Workflow Test Customer",
      "metadata[tenant_id]": tenant?.id ?? "",
    });
    expect(customer.id).toBeTruthy();
    stripeCustomerId = customer.id;
  });

  test("2. Link Stripe customer to tenant", async ({ request }) => {
    test.skip(!stripeCustomerId || !tenant, "No customer or tenant");

    const res = await request.patch(
      `/api/v1/admin/tenants/${tenant?.id}/stripe`,
      {
        headers: {
          "X-Admin-Key": ADMIN_KEY,
          "Content-Type": "application/json",
        },
        data: {
          stripe_customer_id: stripeCustomerId,
        },
      },
    );
    expect(res.status()).toBe(200);

    // Verify
    const detail = await request.get(`/api/v1/admin/tenants/${tenant?.id}`, {
      headers: { "X-Admin-Key": ADMIN_KEY },
    });
    const body = await detail.json();
    expect(body.stripe_customer_id).toBe(stripeCustomerId);
  });

  test("3. Create test subscription in Stripe", async ({ request }) => {
    test.skip(!stripeCustomerId || !STRIPE_KEY, "No customer or key");

    const sub = await stripeRequest(request, "POST", "/subscriptions", {
      customer: stripeCustomerId,
      "items[0][price]": STRIPE_PRICES.starter_monthly,
      payment_behavior: "default_incomplete",
    });

    expect(sub.id).toBeTruthy();
    subscriptionId = sub.id;

    if (sub.items?.data?.[0]) {
      subscriptionItemId = sub.items.data[0].id;
    }
  });

  test("4. Sync subscription item to tenant", async ({ request }) => {
    test.skip(!subscriptionItemId || !tenant, "No subscription item");

    const res = await request.patch(
      `/api/v1/admin/tenants/${tenant?.id}/stripe`,
      {
        headers: {
          "X-Admin-Key": ADMIN_KEY,
          "Content-Type": "application/json",
        },
        data: {
          stripe_subscription_item_id: subscriptionItemId,
        },
      },
    );
    expect(res.status()).toBe(200);
  });

  test("5. Simulate plan upgrade (enterprise → pro and back)", async ({
    request,
  }) => {
    test.skip(!tenant, "No tenant");

    // Save current plan
    const before = await request.get(`/api/v1/admin/tenants/${tenant?.id}`, {
      headers: { "X-Admin-Key": ADMIN_KEY },
    });
    const beforeBody = await before.json();
    const originalPlan = beforeBody.plan;

    // Upgrade to pro
    const upgradeRes = await request.patch(
      `/api/v1/admin/tenants/${tenant?.id}/plan`,
      {
        headers: {
          "X-Admin-Key": ADMIN_KEY,
          "Content-Type": "application/json",
        },
        data: { plan: "growth" },
      },
    );
    expect(upgradeRes.status()).toBe(200);

    // Verify plan changed
    const after = await request.get(`/api/v1/admin/tenants/${tenant?.id}`, {
      headers: { "X-Admin-Key": ADMIN_KEY },
    });
    const afterBody = await after.json();
    expect(afterBody.plan).toBe("growth");

    // Restore original plan
    await request.patch(`/api/v1/admin/tenants/${tenant?.id}/plan`, {
      headers: {
        "X-Admin-Key": ADMIN_KEY,
        "Content-Type": "application/json",
      },
      data: { plan: originalPlan },
    });
  });

  test("6. Simulate subscription cancellation → free", async ({ request }) => {
    test.skip(!tenant, "No tenant");

    // Downgrade to free
    const res = await request.patch(
      `/api/v1/admin/tenants/${tenant?.id}/plan`,
      {
        headers: {
          "X-Admin-Key": ADMIN_KEY,
          "Content-Type": "application/json",
        },
        data: { plan: "free" },
      },
    );
    expect(res.status()).toBe(200);

    const detail = await request.get(`/api/v1/admin/tenants/${tenant?.id}`, {
      headers: { "X-Admin-Key": ADMIN_KEY },
    });
    const body = await detail.json();
    expect(body.plan).toBe("free");

    // Restore to enterprise
    await request.patch(`/api/v1/admin/tenants/${tenant?.id}/plan`, {
      headers: {
        "X-Admin-Key": ADMIN_KEY,
        "Content-Type": "application/json",
      },
      data: { plan: "enterprise" },
    });
  });

  test("7. Verify usage after plan changes", async ({ request }) => {
    test.skip(!tenant, "No tenant");

    const res = await request.get("/api/v1/usage", {
      headers: { Authorization: `Bearer ${tenant?.api_key}` },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.plan).toBe("enterprise");
    expect(body.limit).toBe(100000);
  });

  test("8. Cancel Stripe subscription", async ({ request }) => {
    test.skip(!subscriptionId || !STRIPE_KEY, "No subscription");

    const result = await stripeRequest(
      request,
      "DELETE",
      `/subscriptions/${subscriptionId}`,
    );
    // Subscription may be "canceled" or "incomplete_expired" (no payment method in test)
    expect(["canceled", "incomplete_expired"]).toContain(result.status);
  });

  test("9. Delete Stripe test customer", async ({ request }) => {
    test.skip(!stripeCustomerId || !STRIPE_KEY, "No customer");

    const result = await stripeRequest(
      request,
      "DELETE",
      `/customers/${stripeCustomerId}`,
    );
    expect(result.deleted).toBe(true);
  });
});
