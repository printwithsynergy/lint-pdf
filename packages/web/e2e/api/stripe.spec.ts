import { test, expect } from "@playwright/test";
import { getAdminKey, getTenant } from "../helpers";

test.describe("Stripe Integration (Admin)", () => {
  let adminKey: string;

  test.beforeAll(() => {
    adminKey = getAdminKey();
  });

  test("set and verify Stripe customer ID on tenant", async ({ request }) => {
    const tenant = getTenant("starter");
    test.skip(!adminKey || !tenant, "No admin key or tenant");

    const res = await request.patch(
      `/api/v1/admin/tenants/${tenant?.id}/stripe`,
      {
        headers: {
          "X-Admin-Key": adminKey,
          "Content-Type": "application/json",
        },
        data: {
          stripe_customer_id: "cus_stripe_test_pw",
          stripe_subscription_item_id: "si_stripe_test_pw",
        },
      },
    );
    expect(res.status()).toBe(200);

    const detail = await request.get(`/api/v1/admin/tenants/${tenant?.id}`, {
      headers: { "X-Admin-Key": adminKey },
    });
    expect(detail.status()).toBe(200);
    const body = await detail.json();
    expect(body.stripe_customer_id).toBe("cus_stripe_test_pw");
  });

  test("simulate webhook-driven plan change via admin API", async ({
    request,
  }) => {
    const tenant = getTenant("starter");
    test.skip(!adminKey || !tenant, "No admin key or tenant");

    // First ensure we're at starter baseline
    await request.patch(`/api/v1/admin/tenants/${tenant?.id}/plan`, {
      headers: {
        "X-Admin-Key": adminKey,
        "Content-Type": "application/json",
      },
      data: { plan: "starter" },
    });

    // Simulate: stripe webhook triggers plan upgrade to pro
    const upgradeRes = await request.patch(
      `/api/v1/admin/tenants/${tenant?.id}/plan`,
      {
        headers: {
          "X-Admin-Key": adminKey,
          "Content-Type": "application/json",
        },
        data: {
          plan: "growth",
          overage_enabled: true,
          overage_cap_cents: 5000,
        },
      },
    );
    expect(upgradeRes.status()).toBe(200);

    // Verify limits updated
    const detail = await request.get(`/api/v1/admin/tenants/${tenant?.id}`, {
      headers: { "X-Admin-Key": adminKey },
    });
    const body = await detail.json();
    expect(body.plan).toBe("growth");

    // Revert back to starter
    await request.patch(`/api/v1/admin/tenants/${tenant?.id}/plan`, {
      headers: {
        "X-Admin-Key": adminKey,
        "Content-Type": "application/json",
      },
      data: { plan: "starter" },
    });
  });

  test("simulate subscription cancellation → downgrade to free", async ({
    request,
  }) => {
    const tenant = getTenant("starter");
    test.skip(!adminKey || !tenant, "No admin key or tenant");

    // Ensure baseline is starter
    await request.patch(`/api/v1/admin/tenants/${tenant?.id}/plan`, {
      headers: {
        "X-Admin-Key": adminKey,
        "Content-Type": "application/json",
      },
      data: { plan: "starter" },
    });

    // Downgrade to free (simulates subscription.deleted webhook)
    const res = await request.patch(
      `/api/v1/admin/tenants/${tenant?.id}/plan`,
      {
        headers: {
          "X-Admin-Key": adminKey,
          "Content-Type": "application/json",
        },
        data: { plan: "free" },
      },
    );
    expect(res.status()).toBe(200);

    // Verify
    const detail = await request.get(`/api/v1/admin/tenants/${tenant?.id}`, {
      headers: { "X-Admin-Key": adminKey },
    });
    const body = await detail.json();
    expect(body.plan).toBe("free");

    // Restore to starter
    await request.patch(`/api/v1/admin/tenants/${tenant?.id}/plan`, {
      headers: {
        "X-Admin-Key": adminKey,
        "Content-Type": "application/json",
      },
      data: { plan: "starter" },
    });
  });
});
