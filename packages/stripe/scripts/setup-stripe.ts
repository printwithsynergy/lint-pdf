/**
 * Idempotent Stripe setup script.
 *
 * Creates products, prices (monthly + yearly + metered overage), and portal
 * configuration for LintPDF. Run once per Stripe environment (sandbox or
 * production) — the script searches by product name + price lookup_key so
 * re-runs are safe no-ops.
 *
 * Usage:
 *   STRIPE_SECRET_KEY=sk_test_... npx tsx packages/stripe/scripts/setup-stripe.ts
 *
 * The resulting product/price IDs are written to `.stripe-ids.json` next to
 * this script for reference only — the runtime plan-map in
 * `packages/stripe/src/index.ts` keys on `lookup_key`, not raw IDs, so this
 * file should not be committed (it's gitignored).
 */

import Stripe from "stripe";
import { writeFileSync } from "fs";
import { resolve } from "path";

const STRIPE_SECRET_KEY = process.env.STRIPE_SECRET_KEY;
if (!STRIPE_SECRET_KEY) {
  console.error("Error: STRIPE_SECRET_KEY environment variable is required.");
  process.exit(1);
}

const stripe = new Stripe(STRIPE_SECRET_KEY, {
  apiVersion: "2024-12-18.acacia",
});

interface PlanConfig {
  name: string;
  lookup_key: string;
  monthly_cents: number;
  yearly_cents: number; // 0 means "no yearly price for this plan"
  overage_cents: number;
}

// Keep these in sync with `packages/web/src/lib/brand.ts` (pricingTiers) and
// `packages/stripe/src/index.ts` (planMap). Yearly is ~20% off the monthly
// x 12 list price — adjust per plan before running against prod.
const PLANS: PlanConfig[] = [
  {
    name: "LintPDF Free",
    lookup_key: "lintpdf_free",
    monthly_cents: 0,
    yearly_cents: 0,
    overage_cents: 0,
  },
  {
    name: "LintPDF Viewer",
    lookup_key: "lintpdf_viewer",
    monthly_cents: 1500, // $15/mo — viewer-only tier, no preflight / fill-in / downloads
    yearly_cents: 14400, // $144/yr (~20% off)
    overage_cents: 5,
  },
  {
    name: "LintPDF Starter",
    lookup_key: "lintpdf_starter",
    monthly_cents: 4900,
    yearly_cents: 47000, // $470/yr (~20% off)
    overage_cents: 10,
  },
  {
    name: "LintPDF Growth",
    lookup_key: "lintpdf_growth",
    monthly_cents: 14900,
    yearly_cents: 143000, // $1,430/yr (~20% off)
    overage_cents: 10,
  },
  {
    name: "LintPDF Scale",
    lookup_key: "lintpdf_scale",
    monthly_cents: 39900,
    yearly_cents: 383000, // $3,830/yr (~20% off)
    overage_cents: 10,
  },
  // Enterprise is sales-led — no self-serve checkout price.
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
  recurring: { interval: "month" | "year"; usage_type?: "metered" },
): Promise<string> {
  const existing = await stripe.prices.list({
    product: productId,
    active: true,
    limit: 50,
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
        { interval: "month" },
      );
      ids[`${plan.lookup_key}_monthly`] = priceId;
    }

    if (plan.yearly_cents > 0) {
      const yearlyId = await findOrCreatePrice(
        productId,
        plan.yearly_cents,
        `${plan.lookup_key}_yearly`,
        { interval: "year" },
      );
      ids[`${plan.lookup_key}_yearly`] = yearlyId;
    }

    if (plan.overage_cents > 0) {
      const overagePriceId = await findOrCreatePrice(
        productId,
        plan.overage_cents,
        `${plan.lookup_key}_overage`,
        { interval: "month", usage_type: "metered" },
      );
      ids[`${plan.lookup_key}_overage`] = overagePriceId;
    }
  }

  const outputPath = resolve(import.meta.dirname ?? ".", ".stripe-ids.json");
  writeFileSync(outputPath, JSON.stringify(ids, null, 2));
  console.log(`\nSaved Stripe IDs to ${outputPath}`);
  console.log(
    "\nDone. Legacy 'LintPDF Pro' product — if present in your Stripe account — " +
      "is no longer referenced by this script. Archive it manually in the Stripe " +
      "dashboard once any existing Pro subscriptions have migrated.",
  );
}

main().catch((err) => {
  console.error("Setup failed:", err);
  process.exit(1);
});
