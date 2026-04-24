#!/usr/bin/env tsx
/**
 * Syncs Stripe Product descriptions from the canonical
 * `packages/stripe/PRODUCT_COPY.md` to Stripe Dashboard.
 *
 * Usage:
 *   pnpm --filter @lintpdf/stripe sync:descriptions              # sandbox (default)
 *   pnpm --filter @lintpdf/stripe sync:descriptions -- --live    # live
 *   pnpm --filter @lintpdf/stripe sync:descriptions -- --both    # sandbox + live
 *
 * Env vars:
 *   STRIPE_SECRET_KEY       — live/secondary account secret (sk_live_...)
 *   STRIPE_SDB_SECRET_KEY   — sandbox account secret        (sk_test_...)
 *
 * Products are matched by display name. Stripe products without a matching
 * entry in PRODUCT_COPY.md are left untouched (and reported). Entries in
 * PRODUCT_COPY.md that don't map to a Stripe product are also reported — no
 * silent drift.
 *
 * Name aliases let PRODUCT_COPY.md headings differ from Stripe product
 * names when the dashboard product name is pluralized or rephrased.
 */

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import Stripe from "stripe";

const __dirname = dirname(fileURLToPath(import.meta.url));
const COPY_PATH = resolve(__dirname, "..", "PRODUCT_COPY.md");

// Map PRODUCT_COPY.md heading -> Stripe product name. Only needed when the
// names differ. Keep this table short — if you find yourself adding five
// aliases, rename one side instead.
const NAME_ALIASES: Record<string, string[]> = {
  "AI Credits pack": ["LintPDF AI Credits"],
  "File Pack": ["LintPDF File Packs", "LintPDF File Pack"],
};

interface CopyEntry {
  heading: string;
  description: string;
}

function parseCopy(md: string): CopyEntry[] {
  const lines = md.split(/\r?\n/);
  const entries: CopyEntry[] = [];
  let current: { heading: string; buf: string[] } | null = null;
  const flush = () => {
    if (current) {
      entries.push({
        heading: current.heading,
        description: current.buf.join(" ").trim(),
      });
    }
  };
  for (const line of lines) {
    const h = /^### (.+)$/.exec(line);
    if (h) {
      flush();
      current = { heading: h[1].trim(), buf: [] };
      continue;
    }
    if (current && line.startsWith("> ")) {
      current.buf.push(line.slice(2).trim());
    } else if (current && line.trim() === "") {
      // blank line inside a blockquote is a paragraph break; keep going
    } else if (current && !line.startsWith(">")) {
      flush();
      current = null;
    }
  }
  flush();
  return entries;
}

function resolveKey(mode: "sandbox" | "live"): string {
  const key =
    mode === "live"
      ? process.env.STRIPE_SECRET_KEY
      : process.env.STRIPE_SDB_SECRET_KEY;
  if (!key) {
    throw new Error(
      `Missing Stripe secret key env var for ${mode} mode: ${
        mode === "live" ? "STRIPE_SECRET_KEY" : "STRIPE_SDB_SECRET_KEY"
      }`,
    );
  }
  const prefix = mode === "live" ? "sk_live_" : "sk_test_";
  if (!key.startsWith(prefix)) {
    throw new Error(
      `Stripe key for ${mode} mode does not start with ${prefix} — refusing to run.`,
    );
  }
  return key;
}

async function listAllProducts(stripe: Stripe): Promise<Stripe.Product[]> {
  const out: Stripe.Product[] = [];
  let starting_after: string | undefined;
  for (;;) {
    const page = await stripe.products.list({
      limit: 100,
      starting_after,
      active: true,
    });
    out.push(...page.data);
    if (!page.has_more) break;
    starting_after = page.data[page.data.length - 1]?.id;
    if (!starting_after) break;
  }
  return out;
}

function matchProductsToCopy(
  products: Stripe.Product[],
  copy: CopyEntry[],
): Array<{ product: Stripe.Product; entry: CopyEntry }> {
  const productByName = new Map<string, Stripe.Product>();
  for (const p of products) {
    productByName.set(p.name.trim(), p);
  }
  const pairs: Array<{ product: Stripe.Product; entry: CopyEntry }> = [];
  for (const entry of copy) {
    const candidates = [entry.heading, ...(NAME_ALIASES[entry.heading] ?? [])];
    let matched: Stripe.Product | undefined;
    for (const name of candidates) {
      matched = productByName.get(name);
      if (matched) break;
    }
    if (matched) {
      pairs.push({ product: matched, entry });
    }
  }
  return pairs;
}

async function run(mode: "sandbox" | "live", copy: CopyEntry[]): Promise<void> {
  const stripe = new Stripe(resolveKey(mode), { apiVersion: "2025-09-30.clover" });
  const label = mode.toUpperCase();
  console.log(`\n── [${label}] syncing product descriptions ──`);

  const products = await listAllProducts(stripe);
  const pairs = matchProductsToCopy(products, copy);

  const mappedProductIds = new Set(pairs.map((p) => p.product.id));
  const unmappedProducts = products.filter((p) => !mappedProductIds.has(p.id));
  const unmappedCopy = copy.filter(
    (e) => !pairs.some((p) => p.entry.heading === e.heading),
  );

  let updated = 0;
  let skipped = 0;
  for (const { product, entry } of pairs) {
    if ((product.description ?? "").trim() === entry.description.trim()) {
      console.log(`  [=] ${product.name} — already in sync`);
      skipped += 1;
      continue;
    }
    await stripe.products.update(product.id, {
      description: entry.description,
    });
    console.log(`  [↑] ${product.name} — updated`);
    updated += 1;
  }

  if (unmappedProducts.length) {
    console.log(
      `\n  Stripe products with no PRODUCT_COPY.md entry (untouched):`,
    );
    for (const p of unmappedProducts) console.log(`    · ${p.name} (${p.id})`);
  }
  if (unmappedCopy.length) {
    console.log(
      `\n  PRODUCT_COPY.md entries with no matching Stripe product:`,
    );
    for (const e of unmappedCopy) console.log(`    · ${e.heading}`);
  }

  console.log(
    `\n  [${label}] summary: updated=${updated} unchanged=${skipped} unmapped_products=${unmappedProducts.length} unmapped_copy=${unmappedCopy.length}`,
  );
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const doLive = args.includes("--live") || args.includes("--both");
  const doSandbox =
    args.includes("--sandbox") || args.includes("--both") || !doLive;

  const md = readFileSync(COPY_PATH, "utf8");
  const copy = parseCopy(md);
  if (!copy.length) {
    throw new Error(`PRODUCT_COPY.md contained no ### headings; nothing to sync.`);
  }
  console.log(`Parsed ${copy.length} canonical copy entries.`);

  if (doSandbox) await run("sandbox", copy);
  if (doLive) await run("live", copy);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
