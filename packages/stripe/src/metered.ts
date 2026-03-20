import type Stripe from "stripe";

export function reportOverageUsage(
  stripe: Stripe,
  subscriptionItemId: string,
  quantity: number,
  timestamp?: number,
): Promise<Stripe.UsageRecord> {
  return stripe.subscriptionItems.createUsageRecord(subscriptionItemId, {
    quantity,
    timestamp: timestamp ?? Math.floor(Date.now() / 1000),
    action: "increment",
  });
}
