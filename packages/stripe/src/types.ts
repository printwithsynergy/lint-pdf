export interface OverageEvent {
  tenant_id: string;
  overage_count: number;
  overage_cost_cents: number;
  overage_rate_cents: number;
  stripe_customer_id?: string;
  stripe_subscription_item_id?: string;
}

export interface SetupResult {
  products: Record<string, string>;
  prices: Record<string, string>;
  success: boolean;
}
