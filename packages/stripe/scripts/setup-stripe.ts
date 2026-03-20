/**
 * Idempotent Stripe setup script.
 *
 * Creates products, prices, and portal configuration for LintPDF.
 * Run: npx tsx packages/stripe/scripts/setup-stripe.ts
 *
 * Requires STRIPE_SECRET_KEY environment variable.
 */

import Stripe from "stripe";
import { writeFileSync } from "fs";
import { resolve } from "path";

const STRIPE_SECRET_KEY = process.env.STRIPE_SECRET_KEY;
if (!STRIPE_SECRET_KEY) {
  console.error("Error: STRIPE_SECRET_KEY environment variable is required.");
  process.exit(1); // skipcq: JS-0263 — CLI script requires hard exit on missing config
}

const stripe = new Stripe(STRIPE_SECRET_KEY, {
  apiVersion: "2024-12-18.acacia",
});

interface PlanConfig {
  name: string;
  lookup_key: string;
  monthly_cents: number;
  overage_cents: number;
}

const PLANS: PlanConfig[] = [
  {
    name: "LintPDF Free",
    lookup_key: "grounded_free",
    monthly_cents: 0,
    overage_cents: 0,
  },
  {
    name: "LintPDF Starter",
    lookup_key: "grounded_starter",
    monthly_cents: 4900,
    overage_cents: 10,
  },
  {
    name: "LintPDF Pro",
    lookup_key: "grounded_pro",
    monthly_cents: 14900,
    overage_cents: 10,
  },
  {
    name: "LintPDF Enterprise",
    lookup_key: "grounded_enterprise",
    monthly_cents: 99900,
    overage_cents: 10,
  },
];

async function findOrCreateProduct(
  name: string,
  lookupKey: string,
): Promise<string> {
  const existing = await stripe.products.search({ query: `name:'${name}'` });
  if (existing.data.length > 0) {
    console.log(`  Product "${name}" already exists: ${existing.data[0].id}`);
    return existing.data[0].id;
  }
  const product = await stripe.products.create({
    name,
    metadata: { lookup_key: lookupKey },
  });
  console.log(`  Created product "${name}": ${product.id}`);
  return product.id;
}

async function findOrCreatePrice(
  productId: string,
  unitAmount: number,
  lookupKey: string,
  recurring: { interval: "month"; usage_type?: "metered" },
): Promise<string> {
  const existing = await stripe.prices.list({
    product: productId,
    active: true,
    limit: 10,
  });
  for (const price of existing.data) {
    if (
      price.unit_amount === unitAmount &&
      price.recurring?.interval === recurring.interval &&
      (price.recurring?.usage_type || "licensed") ===
        (recurring.usage_type || "licensed")
    ) {
      console.log(`  Price ${lookupKey} already exists: ${price.id}`);
      return price.id;
    }
  }
  const price = await stripe.prices.create({
    product: productId,
    unit_amount: unitAmount,
    currency: "usd",
    recurring,
    lookup_key: lookupKey,
    metadata: { lookup_key: lookupKey },
  });
  console.log(`  Created price ${lookupKey}: ${price.id}`);
  return price.id;
}

async function main() {
  console.log("Setting up Stripe for LintPDF...\n");

  const ids: Record<string, string> = {};

  for (const plan of PLANS) {
    console.log(`\n${plan.name}:`);
    const productId = await findOrCreateProduct(plan.name, plan.lookup_key);
    ids[`${plan.lookup_key}_product`] = productId;

    if (plan.monthly_cents > 0) {
      const priceId = await findOrCreatePrice(
        productId,
        plan.monthly_cents,
        `${plan.lookup_key}_monthly`,
        {
          interval: "month",
        },
      );
      ids[`${plan.lookup_key}_monthly`] = priceId;
    }

    if (plan.overage_cents > 0) {
      const overagePriceId = await findOrCreatePrice(
        productId,
        plan.overage_cents,
        `${plan.lookup_key}_overage`,
        {
          interval: "month",
          usage_type: "metered",
        },
      );
      ids[`${plan.lookup_key}_overage`] = overagePriceId;
    }
  }

  // Save IDs
  const outputPath = resolve(import.meta.dirname ?? ".", ".stripe-ids.json");
  writeFileSync(outputPath, JSON.stringify(ids, null, 2));
  console.log(`\nSaved Stripe IDs to ${outputPath}`);
  console.log("\nDone! Copy the price IDs into your PricingSection.tsx URLs.");
}

main().catch((err) => {
  console.error("Setup failed:", err);
  process.exit(1); // skipcq: JS-0263 — CLI script requires hard exit on failure
});
