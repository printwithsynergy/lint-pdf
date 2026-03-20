import { describe, it, expect, vi, beforeEach } from "vitest";
import type { PluginContext } from "@thinkneverland/pixie-dust-fairy-ring";

// Mock stripe-kit functions
vi.mock("@thinkneverland/pixie-dust-stripe-kit", () => ({
  getStripe: vi.fn(),
  findOrCreateCustomer: vi.fn(),
  createCheckoutSession: vi.fn(),
  createPortalSession: vi.fn(),
  listInvoices: vi.fn(),
  getSubscription: vi.fn(),
}));

// Mock metered module
vi.mock("../src/metered.js", () => ({
  reportOverageUsage: vi.fn(),
}));

import {
  getStripe,
  findOrCreateCustomer,
  createCheckoutSession,
  createPortalSession,
  listInvoices,
} from "@thinkneverland/pixie-dust-stripe-kit";

/** Create a mock context object with all required service stubs. */
function createMockContext() {
  return {
    addRoutes: vi.fn(),
    addNavItem: vi.fn(),
    addPage: vi.fn(),
    addPermission: vi.fn(),
    addRole: vi.fn(),
    addPublicPath: vi.fn(),
    on: vi.fn(),
    emit: vi.fn(),
    services: {
      logger: {
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
        debug: vi.fn(),
      },
      db: {
        subscription: { findFirst: vi.fn() },
        stripeCustomer: { findFirst: vi.fn() },
      },
      auth: {},
      config: {},
    },
  };
}

/** Cast a mock context to PluginContext for use with plugin methods. */
function asPluginContext(
  ctx: ReturnType<typeof createMockContext>,
): PluginContext {
  return ctx as PluginContext;
}

/** Create a mock Stripe instance (empty object satisfying the return type). */
function createMockStripeInstance(): ReturnType<typeof getStripe> {
  return {} as ReturnType<typeof getStripe>;
}

/** Create a null Stripe instance (simulating unconfigured Stripe). */
function createNullStripeInstance(): ReturnType<typeof getStripe> {
  return null as ReturnType<typeof getStripe>;
}

describe("groundedBillingPlugin", () => {
  let ctx: ReturnType<typeof createMockContext>;

  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    ctx = createMockContext();
  });

  // ── Registration tests ──────────────────────────────────────

  describe("register", () => {
    it("registers billing:manage permission for ADMIN and OWNER", async () => {
      const mod = await import("../src/index.js");
      mod.groundedBillingPlugin.register?.(asPluginContext(ctx));

      expect(ctx.addPermission).toHaveBeenCalledWith("billing:manage", [
        "ADMIN",
        "OWNER",
      ]);
    });

    it("registers Billing nav item in admin section", async () => {
      const mod = await import("../src/index.js");
      mod.groundedBillingPlugin.register?.(asPluginContext(ctx));

      expect(ctx.addNavItem).toHaveBeenCalledWith(
        expect.objectContaining({
          label: "Billing",
          href: "/dashboard/billing",
          icon: "credit-card",
          section: "admin",
          requiredPermission: "billing:manage",
          excludeRoles: ["SUPER_ADMIN"],
        }),
      );
    });

    it("registers billing pages", async () => {
      const mod = await import("../src/index.js");
      mod.groundedBillingPlugin.register?.(asPluginContext(ctx));

      expect(ctx.addPage).toHaveBeenCalledTimes(2);
      expect(ctx.addPage).toHaveBeenCalledWith(
        expect.objectContaining({ path: "/dashboard/billing" }),
      );
      expect(ctx.addPage).toHaveBeenCalledWith(
        expect.objectContaining({ path: "/dashboard/billing/invoices" }),
      );
    });

    it("registers routes under /api/grounded/billing", async () => {
      const mod = await import("../src/index.js");
      mod.groundedBillingPlugin.register?.(asPluginContext(ctx));

      expect(ctx.addRoutes).toHaveBeenCalledTimes(1);
      const [prefix, routes] = ctx.addRoutes.mock.calls[0];
      expect(prefix).toBe("/api/grounded/billing");
      expect(routes.length).toBe(4);
    });

    it("registers 4 webhook event listeners", async () => {
      const mod = await import("../src/index.js");
      mod.groundedBillingPlugin.register?.(asPluginContext(ctx));

      expect(ctx.on).toHaveBeenCalledTimes(4);
      expect(ctx.on).toHaveBeenCalledWith(
        "stripe:customer.subscription.updated",
        expect.any(Function),
      );
      expect(ctx.on).toHaveBeenCalledWith(
        "stripe:customer.subscription.deleted",
        expect.any(Function),
      );
      expect(ctx.on).toHaveBeenCalledWith(
        "stripe:invoice.payment_failed",
        expect.any(Function),
      );
      expect(ctx.on).toHaveBeenCalledWith(
        "stripe:invoice.payment_succeeded",
        expect.any(Function),
      );
    });

    it("has correct plugin metadata", async () => {
      const mod = await import("../src/index.js");
      expect(mod.groundedBillingPlugin.name).toBe("grounded-billing");
      expect(mod.groundedBillingPlugin.version).toBe("0.1.0");
      expect(mod.groundedBillingPlugin.dependencies).toContain("stripe-kit");
    });
  });

  // ── Route handler tests ─────────────────────────────────────

  describe("route handlers", () => {
    async function getRouteHandler(method: string, path: string) {
      const mod = await import("../src/index.js");
      mod.groundedBillingPlugin.register?.(asPluginContext(ctx));
      const [, routes] = ctx.addRoutes.mock.calls[0];
      const route = routes.find(
        (r: { method: string; path: string }) =>
          r.method === method && r.path === path,
      );
      return route?.handler;
    }

    describe("POST /checkout", () => {
      it("returns 503 when Stripe is not configured", async () => {
        vi.mocked(getStripe).mockReturnValue(createNullStripeInstance());
        const handler = await getRouteHandler("POST", "/checkout");

        const res = await handler({
          body: { priceId: "price_123", successUrl: "/ok", cancelUrl: "/no" },
          auth: { tenantId: "t1", email: "a@b.com" },
        });

        expect(res.status).toBe(503);
        expect(res.body.error).toBe("Stripe not configured");
      });

      it("returns 401 when tenant context is missing", async () => {
        vi.mocked(getStripe).mockReturnValue(createMockStripeInstance());
        const handler = await getRouteHandler("POST", "/checkout");

        const res = await handler({
          body: { priceId: "price_123", successUrl: "/ok", cancelUrl: "/no" },
          auth: {},
        });

        expect(res.status).toBe(401);
      });

      it("creates checkout session and returns session ID and URL", async () => {
        const mockStripeInstance = createMockStripeInstance();
        vi.mocked(getStripe).mockReturnValue(mockStripeInstance);
        vi.mocked(findOrCreateCustomer).mockResolvedValue("cus_123");
        vi.mocked(createCheckoutSession).mockResolvedValue({
          id: "cs_123",
          url: "https://checkout.stripe.com/session",
        } as Awaited<ReturnType<typeof createCheckoutSession>>);

        const handler = await getRouteHandler("POST", "/checkout");
        const res = await handler({
          body: {
            priceId: "price_abc",
            successUrl: "/success",
            cancelUrl: "/cancel",
          },
          auth: { tenantId: "tenant_1", email: "user@test.com" },
        });

        expect(res.status).toBe(200);
        expect(res.body).toEqual({
          sessionId: "cs_123",
          url: "https://checkout.stripe.com/session",
        });
        expect(createCheckoutSession).toHaveBeenCalledWith(
          mockStripeInstance,
          expect.objectContaining({
            customerId: "cus_123",
            tenantId: "tenant_1",
            priceId: "price_abc",
            mode: "subscription",
          }),
        );
      });
    });

    describe("POST /portal", () => {
      it("returns 503 when Stripe is not configured", async () => {
        vi.mocked(getStripe).mockReturnValue(createNullStripeInstance());
        const handler = await getRouteHandler("POST", "/portal");

        const res = await handler({
          body: { returnUrl: "/billing" },
          auth: { tenantId: "t1", email: "a@b.com" },
        });

        expect(res.status).toBe(503);
      });

      it("returns 401 when tenant context is missing", async () => {
        vi.mocked(getStripe).mockReturnValue(createMockStripeInstance());
        const handler = await getRouteHandler("POST", "/portal");

        const res = await handler({
          body: { returnUrl: "/billing" },
          auth: {},
        });

        expect(res.status).toBe(401);
      });

      it("creates portal session and returns URL", async () => {
        vi.mocked(getStripe).mockReturnValue(createMockStripeInstance());
        vi.mocked(findOrCreateCustomer).mockResolvedValue("cus_456");
        vi.mocked(createPortalSession).mockResolvedValue({
          url: "https://billing.stripe.com/portal",
        } as Awaited<ReturnType<typeof createPortalSession>>);

        const handler = await getRouteHandler("POST", "/portal");
        const res = await handler({
          body: { returnUrl: "/dashboard/billing" },
          auth: { tenantId: "tenant_1", email: "user@test.com" },
        });

        expect(res.status).toBe(200);
        expect(res.body).toEqual({ url: "https://billing.stripe.com/portal" });
      });
    });

    describe("GET /subscription", () => {
      it("returns 503 when Stripe is not configured", async () => {
        vi.mocked(getStripe).mockReturnValue(createNullStripeInstance());
        const handler = await getRouteHandler("GET", "/subscription");

        const res = await handler({ auth: { tenantId: "t1" } });
        expect(res.status).toBe(503);
      });

      it("returns 401 when tenant context is missing", async () => {
        vi.mocked(getStripe).mockReturnValue(createMockStripeInstance());
        const handler = await getRouteHandler("GET", "/subscription");

        const res = await handler({ auth: {} });
        expect(res.status).toBe(401);
      });

      it("returns free plan when no subscription exists", async () => {
        vi.mocked(getStripe).mockReturnValue(createMockStripeInstance());
        ctx.services.db.subscription.findFirst.mockResolvedValue(null);

        const handler = await getRouteHandler("GET", "/subscription");
        const res = await handler({ auth: { tenantId: "t1" } });

        expect(res.status).toBe(200);
        expect(res.body).toEqual({ plan: "free", status: "none" });
      });

      it("returns subscription when it exists", async () => {
        vi.mocked(getStripe).mockReturnValue(createMockStripeInstance());
        const sub = { plan: "growth", status: "active", tenantId: "t1" };
        ctx.services.db.subscription.findFirst.mockResolvedValue(sub);

        const handler = await getRouteHandler("GET", "/subscription");
        const res = await handler({ auth: { tenantId: "t1" } });

        expect(res.status).toBe(200);
        expect(res.body).toEqual(sub);
      });
    });

    describe("GET /invoices", () => {
      it("returns 503 when Stripe is not configured", async () => {
        vi.mocked(getStripe).mockReturnValue(createNullStripeInstance());
        const handler = await getRouteHandler("GET", "/invoices");

        const res = await handler({ auth: { tenantId: "t1" } });
        expect(res.status).toBe(503);
      });

      it("returns empty array when no customer exists", async () => {
        vi.mocked(getStripe).mockReturnValue(createMockStripeInstance());
        ctx.services.db.stripeCustomer.findFirst.mockResolvedValue(null);

        const handler = await getRouteHandler("GET", "/invoices");
        const res = await handler({ auth: { tenantId: "t1" } });

        expect(res.status).toBe(200);
        expect(res.body).toEqual({ invoices: [] });
      });

      it("returns invoices when customer exists", async () => {
        const stripeInstance = createMockStripeInstance();
        vi.mocked(getStripe).mockReturnValue(stripeInstance);
        ctx.services.db.stripeCustomer.findFirst.mockResolvedValue({
          stripeCustomerId: "cus_789",
        });
        const invoiceData = [{ id: "inv_1" }, { id: "inv_2" }];
        vi.mocked(listInvoices).mockResolvedValue(
          invoiceData as Awaited<ReturnType<typeof listInvoices>>,
        );

        const handler = await getRouteHandler("GET", "/invoices");
        const res = await handler({ auth: { tenantId: "t1" } });

        expect(res.status).toBe(200);
        expect(res.body).toEqual({ invoices: invoiceData });
        expect(listInvoices).toHaveBeenCalledWith(stripeInstance, "cus_789");
      });
    });
  });

  // ── Webhook handler tests ──────────────────────────────────

  describe("webhook handlers", () => {
    function getWebhookHandler(eventName: string) {
      const call = ctx.on.mock.calls.find((c: unknown[]) => c[0] === eventName);
      return call?.[1];
    }

    describe("stripe:customer.subscription.updated", () => {
      it("does nothing when subscription data is missing", async () => {
        const mod = await import("../src/index.js");
        mod.groundedBillingPlugin.register?.(asPluginContext(ctx));
        const handler = getWebhookHandler(
          "stripe:customer.subscription.updated",
        );

        await handler({ data: {} });
        expect(ctx.services.db.stripeCustomer.findFirst).not.toHaveBeenCalled();
      });

      it("does nothing when customer ID is missing", async () => {
        const mod = await import("../src/index.js");
        mod.groundedBillingPlugin.register?.(asPluginContext(ctx));
        const handler = getWebhookHandler(
          "stripe:customer.subscription.updated",
        );

        await handler({ data: { object: { customer: null } } });
        expect(ctx.services.db.stripeCustomer.findFirst).not.toHaveBeenCalled();
      });

      it("logs warning when no tenant found for customer", async () => {
        const mod = await import("../src/index.js");
        mod.groundedBillingPlugin.register?.(asPluginContext(ctx));
        const handler = getWebhookHandler(
          "stripe:customer.subscription.updated",
        );
        ctx.services.db.stripeCustomer.findFirst.mockResolvedValue(null);

        await handler({
          data: {
            object: {
              customer: "cus_123",
              items: {
                data: [
                  { price: { lookup_key: "grounded_pro_monthly" }, id: "si_1" },
                ],
              },
            },
          },
        });

        expect(ctx.services.logger.warn).toHaveBeenCalledWith(
          "Stripe subscription update: no tenant found for customer",
          { customerId: "cus_123" },
        );
      });

      it("handles customer as object with id property", async () => {
        const mod = await import("../src/index.js");
        mod.groundedBillingPlugin.register?.(asPluginContext(ctx));
        const handler = getWebhookHandler(
          "stripe:customer.subscription.updated",
        );
        ctx.services.db.stripeCustomer.findFirst.mockResolvedValue(null);

        await handler({
          data: {
            object: {
              customer: { id: "cus_obj_123" },
              items: { data: [] },
            },
          },
        });

        expect(ctx.services.db.stripeCustomer.findFirst).toHaveBeenCalledWith({
          where: { stripeCustomerId: "cus_obj_123" },
        });
      });
    });

    describe("stripe:customer.subscription.deleted", () => {
      it("does nothing when subscription data is missing", async () => {
        const mod = await import("../src/index.js");
        mod.groundedBillingPlugin.register?.(asPluginContext(ctx));
        const handler = getWebhookHandler(
          "stripe:customer.subscription.deleted",
        );

        await handler({ data: {} });
        expect(ctx.services.db.stripeCustomer.findFirst).not.toHaveBeenCalled();
      });

      it("does nothing when no tenant found", async () => {
        const mod = await import("../src/index.js");
        mod.groundedBillingPlugin.register?.(asPluginContext(ctx));
        const handler = getWebhookHandler(
          "stripe:customer.subscription.deleted",
        );
        ctx.services.db.stripeCustomer.findFirst.mockResolvedValue(null);

        await handler({
          data: { object: { customer: "cus_unknown" } },
        });

        // No error logged because no customerRecord found
        expect(ctx.services.logger.error).not.toHaveBeenCalled();
      });
    });

    describe("stripe:invoice.payment_failed", () => {
      it("logs warning with event ID", async () => {
        const mod = await import("../src/index.js");
        mod.groundedBillingPlugin.register?.(asPluginContext(ctx));
        const handler = getWebhookHandler("stripe:invoice.payment_failed");

        await handler({ id: "evt_123" });

        expect(ctx.services.logger.warn).toHaveBeenCalledWith(
          "Stripe: invoice payment failed",
          { eventId: "evt_123" },
        );
      });
    });

    describe("stripe:invoice.payment_succeeded", () => {
      it("logs info with event ID", async () => {
        const mod = await import("../src/index.js");
        mod.groundedBillingPlugin.register?.(asPluginContext(ctx));
        const handler = getWebhookHandler("stripe:invoice.payment_succeeded");

        await handler({ id: "evt_456" });

        expect(ctx.services.logger.info).toHaveBeenCalledWith(
          "Stripe: invoice payment succeeded",
          { eventId: "evt_456" },
        );
      });
    });
  });

  // ── Boot & shutdown ─────────────────────────────────────────

  describe("boot", () => {
    it("logs ready message when Stripe is configured", async () => {
      vi.mocked(getStripe).mockReturnValue(createMockStripeInstance());
      const mod = await import("../src/index.js");
      await mod.groundedBillingPlugin.boot?.(asPluginContext(ctx));

      expect(ctx.services.logger.info).toHaveBeenCalledWith(
        "LintPDF billing plugin ready",
      );
    });

    it("does not log when Stripe is not configured", async () => {
      vi.mocked(getStripe).mockReturnValue(createNullStripeInstance());
      const mod = await import("../src/index.js");
      await mod.groundedBillingPlugin.boot?.(asPluginContext(ctx));

      expect(ctx.services.logger.info).not.toHaveBeenCalled();
    });
  });

  describe("shutdown", () => {
    it("completes without error", async () => {
      const mod = await import("../src/index.js");
      const result = mod.groundedBillingPlugin.shutdown?.();
      if (result !== undefined) {
        await expect(result).resolves.toBeUndefined();
      }
    });
  });
});
