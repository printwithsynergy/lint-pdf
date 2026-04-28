/**
 * LintPDF Billing — Fairy Ring plugin extending stripe-kit.
 *
 * Adds LintPDF-specific billing features on top of Pixie Dust's stripe-kit:
 * - Checkout + portal integration for LintPDF subscription plans
 * - Metered overage billing (per-job charges beyond plan limits)
 * - Plan sync to the LintPDF engine via admin API
 */

import type {
  PixieDustPlugin,
  PluginContext,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";
import {
  getStripe,
  findOrCreateCustomer,
  createCheckoutSession,
  createPortalSession,
  listInvoices,
} from "@thinkneverland/pixie-dust-stripe-kit";

export { reportOverageUsage } from "./metered.js";
export type { OverageEvent, SetupResult } from "./types.js";

// ── Engine admin API helper ─────────────────────────────────

function engineAdminUrl(): string {
  const url = process.env.LINTPDF_API_URL ?? "http://localhost:8000";
  return url.replace(/\/$/, "");
}

function adminHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const key = process.env.LINTPDF_ADMIN_API_KEY;
  if (key) headers["X-Admin-Key"] = key;
  return headers;
}

async function syncPlanToEngine(tenantId: string, plan: string): Promise<void> {
  const res = await fetch(
    `${engineAdminUrl()}/api/v1/admin/tenants/${tenantId}/plan`,
    {
      method: "PATCH",
      headers: adminHeaders(),
      body: JSON.stringify({ plan }),
    },
  );
  if (!res.ok) {
    throw new Error(
      `Failed to sync plan to engine: ${res.status} ${res.statusText}`,
    );
  }
}

async function syncStripeIds(
  tenantId: string,
  customerId: string,
  subscriptionItemId?: string,
): Promise<void> {
  const res = await fetch(
    `${engineAdminUrl()}/api/v1/admin/tenants/${tenantId}/stripe`,
    {
      method: "PATCH",
      headers: adminHeaders(),
      body: JSON.stringify({
        stripe_customer_id: customerId,
        stripe_subscription_item_id: subscriptionItemId ?? null,
      }),
    },
  );
  if (!res.ok) {
    throw new Error(
      `Failed to sync Stripe IDs to engine: ${res.status} ${res.statusText}`,
    );
  }
}

// ── Plugin definition ───────────────────────────────────────

// ── Internal type helpers ────────────────────────────────────
// The Prisma-style DB client shape used by billing routes/hooks.
interface BillingDb {
  subscription: {
    findFirst: (args: Record<string, unknown>) => Promise<unknown>;
  };
  stripeCustomer: {
    findFirst: (
      args: Record<string, unknown>,
    ) => Promise<{ tenantId: string; stripeCustomerId: string } | null>;
  };
}

interface StripeWebhookEvent {
  id?: string;
  data?: {
    object?: {
      customer?: string | { id: string };
      items?: { data?: Array<{ id: string; price?: { lookup_key?: string } }> };
    };
  };
}

export const lintpdfBillingPlugin: PixieDustPlugin = {
  name: "lintpdf-billing",
  version: "0.1.0",
  description:
    "LintPDF billing — extends stripe-kit with plans, checkout, portal, and metered overage",
  dependencies: ["stripe-kit"],

  register(ctx: PluginContext): void {
    ctx.addPermission("billing:manage", ["ADMIN", "OWNER"]);

    ctx.addNavItem({
      label: "Billing",
      href: "/dashboard/billing",
      icon: "credit-card",
      section: "tenant",
      order: 15,
      requiredPermission: "billing:manage",
    });

    ctx.addPage({
      path: "/dashboard/billing",
      title: "Billing & Subscription",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/billing/invoices",
      title: "Invoices",
      layout: "dashboard",
    });

    // ── Routes ──
    ctx.addRoutes("/api/lintpdf/billing", [
      {
        method: "POST",
        path: "/checkout",
        auth: true,
        permission: "billing:manage",
        description: "Create a Stripe Checkout session for plan subscription",
        handler: async (req: RouteRequest): Promise<RouteResponse> => {
          const stripe = getStripe();
          if (!stripe) {
            return { status: 503, body: { error: "Stripe not configured" } };
          }
          const { priceId, successUrl, cancelUrl } = req.body as {
            priceId: string;
            successUrl: string;
            cancelUrl: string;
          };
          const tenantId = req.auth?.tenantId;
          if (!tenantId || !req.auth?.email) {
            return { status: 401, body: { error: "Tenant context required" } };
          }

          const db = ctx.services.db as BillingDb;
          const customerId = await findOrCreateCustomer(
            stripe,
            db,
            tenantId,
            req.auth.email,
          );
          const session = await createCheckoutSession(stripe, {
            customerId,
            tenantId,
            priceId,
            successUrl,
            cancelUrl,
            mode: "subscription",
          });

          return {
            status: 200,
            body: { sessionId: session.id, url: session.url },
          };
        },
      },
      {
        method: "POST",
        path: "/portal",
        auth: true,
        permission: "billing:manage",
        description: "Create a Stripe Customer Portal session",
        handler: async (req: RouteRequest): Promise<RouteResponse> => {
          const stripe = getStripe();
          if (!stripe) {
            return { status: 503, body: { error: "Stripe not configured" } };
          }
          const { returnUrl } = req.body as { returnUrl: string };
          const tenantId = req.auth?.tenantId;
          if (!tenantId || !req.auth?.email) {
            return { status: 401, body: { error: "Tenant context required" } };
          }

          const db = ctx.services.db as BillingDb;
          const customerId = await findOrCreateCustomer(
            stripe,
            db,
            tenantId,
            req.auth.email,
          );
          const session = await createPortalSession(
            stripe,
            customerId,
            returnUrl,
          );

          return { status: 200, body: { url: session.url } };
        },
      },
      {
        method: "GET",
        path: "/subscription",
        auth: true,
        permission: "billing:manage",
        description: "Get current subscription status",
        handler: async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 401, body: { error: "Tenant context required" } };
          }

          // When Stripe isn't configured (e.g. self-hosted dev or
          // tenant-test environment) we don't 503 — the dashboard's
          // billing page should render the same empty "free / none"
          // card it shows when no Stripe customer exists. Surface
          // `stripe_unavailable` so the UI can optionally hide upgrade
          // affordances.
          const stripe = getStripe();
          if (!stripe) {
            return {
              status: 200,
              body: {
                plan: "free",
                status: "none",
                stripe_unavailable: true,
              },
            };
          }

          const db = ctx.services.db as BillingDb;
          const subscription = await db.subscription.findFirst({
            where: { tenantId },
            orderBy: { createdAt: "desc" },
          });

          if (!subscription) {
            return { status: 200, body: { plan: "free", status: "none" } };
          }

          return { status: 200, body: subscription };
        },
      },
      {
        method: "GET",
        path: "/invoices",
        auth: true,
        permission: "billing:manage",
        description: "List invoices for the current tenant",
        handler: async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 401, body: { error: "Tenant context required" } };
          }

          // Same graceful-fallback rule as /subscription: missing
          // Stripe config returns an empty list rather than 503.
          const stripe = getStripe();
          if (!stripe) {
            return { status: 200, body: { invoices: [] } };
          }

          const db = ctx.services.db as BillingDb;
          const customer = await db.stripeCustomer.findFirst({
            where: { tenantId },
          });

          if (!customer) {
            return { status: 200, body: { invoices: [] } };
          }

          const invoices = await listInvoices(
            stripe,
            customer.stripeCustomerId,
          );
          return { status: 200, body: { invoices } };
        },
      },
    ]);

    // ── Stripe webhook hook listeners ──
    ctx.on("stripe:customer.subscription.updated", async (data) => {
      const event = data as StripeWebhookEvent;
      const subscription = event.data?.object;
      if (!subscription) return;

      const customerId =
        typeof subscription.customer === "string"
          ? subscription.customer
          : subscription.customer?.id;

      if (!customerId) return;

      // Look up tenant by Stripe customer ID
      const db = ctx.services.db as BillingDb;
      const customerRecord = await db.stripeCustomer.findFirst({
        where: { stripeCustomerId: customerId },
      });

      if (!customerRecord) {
        ctx.services.logger.warn(
          "Stripe subscription update: no tenant found for customer",
          {
            customerId,
          },
        );
        return;
      }

      // Map Stripe price lookup_key → LintPDF engine plan name. Monthly
      // and yearly prices both resolve to the same engine plan — the
      // billing cadence is a Stripe concern, not an entitlement one.
      // Keep in sync with `packages/stripe/scripts/setup-stripe.ts`.
      const priceId = subscription.items?.data?.[0]?.price?.lookup_key;
      const planMap: Record<string, string> = {
        lintpdf_viewer_monthly: "viewer",
        lintpdf_viewer_yearly: "viewer",
        lintpdf_starter_monthly: "starter",
        lintpdf_starter_yearly: "starter",
        lintpdf_growth_monthly: "growth",
        lintpdf_growth_yearly: "growth",
        lintpdf_scale_monthly: "scale",
        lintpdf_scale_yearly: "scale",
        lintpdf_enterprise_monthly: "enterprise",
        lintpdf_enterprise_yearly: "enterprise",
      };
      const plan = (priceId != null ? planMap[priceId] : undefined) ?? "free";

      try {
        await syncPlanToEngine(customerRecord.tenantId, plan);

        // Sync subscription item ID for metered billing
        const subscriptionItemId = subscription.items?.data?.[0]?.id;
        if (subscriptionItemId) {
          await syncStripeIds(
            customerRecord.tenantId,
            customerId,
            subscriptionItemId,
          );
        }

        ctx.services.logger.info("Plan synced to engine", {
          tenantId: customerRecord.tenantId,
          plan,
        });
      } catch (err) {
        ctx.services.logger.error("Failed to sync plan/Stripe IDs to engine", {
          tenantId: customerRecord.tenantId,
          plan,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    });

    ctx.on("stripe:customer.subscription.deleted", async (data) => {
      const event = data as StripeWebhookEvent;
      const subscription = event.data?.object;
      if (!subscription) return;

      const customerId =
        typeof subscription.customer === "string"
          ? subscription.customer
          : subscription.customer?.id;

      if (!customerId) return;

      const db = ctx.services.db as BillingDb;
      const customerRecord = await db.stripeCustomer.findFirst({
        where: { stripeCustomerId: customerId },
      });

      if (customerRecord) {
        try {
          await syncPlanToEngine(customerRecord.tenantId, "free");
          ctx.services.logger.info("Tenant downgraded to free", {
            tenantId: customerRecord.tenantId,
          });
        } catch (err) {
          ctx.services.logger.error(
            "Failed to downgrade tenant plan in engine",
            {
              tenantId: customerRecord.tenantId,
              error: err instanceof Error ? err.message : String(err),
            },
          );
        }
      }
    });

    ctx.on("stripe:invoice.payment_failed", (data) => {
      ctx.services.logger.warn("Stripe: invoice payment failed", {
        eventId: (data as StripeWebhookEvent)?.id,
      });
    });

    ctx.on("stripe:invoice.payment_succeeded", (data) => {
      ctx.services.logger.info("Stripe: invoice payment succeeded", {
        eventId: (data as StripeWebhookEvent)?.id,
      });
    });
  },

  boot(ctx: PluginContext): void {
    const stripe = getStripe();
    if (stripe) {
      ctx.services.logger.info("LintPDF billing plugin ready");
    }
  },

  shutdown(): void {
    // No cleanup needed — stripe-kit handles its own shutdown
  },
};

export default lintpdfBillingPlugin;
