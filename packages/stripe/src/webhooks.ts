/**
 * Stripe webhook handling is now managed by stripe-kit via Fairy Ring hooks.
 *
 * The lintpdfBillingPlugin listens to these hooks in its register() method:
 * - stripe:customer.subscription.updated → sync plan to engine
 * - stripe:customer.subscription.deleted → downgrade to free
 * - stripe:invoice.payment_failed → log warning
 * - stripe:invoice.payment_succeeded → log confirmation
 *
 * This file is kept for backwards compatibility of any imports.
 */

export {
  verifyWebhookSignature,
  processWebhookEvent,
} from "@thinkneverland/pixie-dust-stripe-kit";
