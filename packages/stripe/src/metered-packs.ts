/**
 * Metered-resource pack catalogue.
 *
 * Two "kinds" of resources are sold as one-off top-ups alongside the
 * plan subscription: AI credits and file packs. Each kind has three
 * fixed-size packs; the Stripe price ids for both live + sandbox are
 * hardcoded below and overridable via env vars at runtime.
 *
 * Kept together in one file so the dashboard "Buy more" flow and the
 * engine's `/topup` endpoint see the same truth. To add a new pack
 * size, bump this file AND `packages/engine/src/lintpdf/billing/metered_packs.py`
 * in the same commit.
 */

export type PackKind = "credits" | "files";

export interface PackDef {
  kind: PackKind;
  size: number;
  usdCents: number;
  /** Live-mode Stripe price id (real charges). */
  priceIdLive: string;
  /** Sandbox (test-mode) Stripe price id. */
  priceIdSandbox: string;
}

// IDs minted via packages/stripe/scripts/sync-metered-packs.ts on 2026-04-17.
// Override per-deploy with LINTPDF_STRIPE_PRICE_<KIND>_<SIZE>{_SANDBOX}?
export const METERED_PACKS: Record<string, PackDef> = {
  credits_500: {
    kind: "credits",
    size: 500,
    usdCents: 2500,
    priceIdLive: "price_1TNHg8GdPozm4cl0SO01uMtG",
    priceIdSandbox: "price_1TNHfgKIaHHghEpJHwagKqXs",
  },
  credits_2000: {
    kind: "credits",
    size: 2000,
    usdCents: 9000,
    priceIdLive: "price_1TNHg9GdPozm4cl0oP7z40Xo",
    priceIdSandbox: "price_1TNHfhKIaHHghEpJ4YbG4OsC",
  },
  credits_10000: {
    kind: "credits",
    size: 10000,
    usdCents: 40000,
    priceIdLive: "price_1TNHg9GdPozm4cl0GrqMkwlI",
    priceIdSandbox: "price_1TNHfhKIaHHghEpJ60lJbmr7",
  },
  files_500: {
    kind: "files",
    size: 500,
    usdCents: 1500,
    priceIdLive: "price_1TNHgAGdPozm4cl0vpKicGI3",
    priceIdSandbox: "price_1TNHfiKIaHHghEpJl9lhXeFU",
  },
  files_2500: {
    kind: "files",
    size: 2500,
    usdCents: 6000,
    priceIdLive: "price_1TNHgBGdPozm4cl0DzqAnsj5",
    priceIdSandbox: "price_1TNHfiKIaHHghEpJe8f7M74R",
  },
  files_10000: {
    kind: "files",
    size: 10000,
    usdCents: 20000,
    priceIdLive: "price_1TNHgBGdPozm4cl0LAVPzdGv",
    priceIdSandbox: "price_1TNHfjKIaHHghEpJv0Xsxp7G",
  },
};

export function resolvePriceId(
  packKey: keyof typeof METERED_PACKS,
  opts?: { sandbox?: boolean },
): string {
  const def = METERED_PACKS[packKey];
  if (!def) throw new Error(`Unknown pack: ${packKey}`);
  const envOverride =
    process.env[
      `LINTPDF_STRIPE_PRICE_${def.kind.toUpperCase()}_${def.size}${opts?.sandbox ? "_SANDBOX" : ""}`
    ];
  return envOverride ?? (opts?.sandbox ? def.priceIdSandbox : def.priceIdLive);
}

export function listPacks(kind: PackKind): PackDef[] {
  return Object.values(METERED_PACKS).filter((p) => p.kind === kind);
}
