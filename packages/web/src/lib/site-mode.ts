/**
 * Build-time site posture flag.
 *
 * Controls whether the public marketing surface renders the full commercial
 * SaaS pitch ("saas" mode) or a low-pressure detection-only product
 * description with no signup CTAs ("oss" mode). The flag exists so we can
 * pivot the public posture on short notice without rewriting copy or
 * forking the codebase.
 *
 * The Railway env var name is NEXT_PUBLIC_ENABLE_SAAS — it must carry the
 * NEXT_PUBLIC_ prefix because Header / Footer / HeroSection are client
 * components and Next.js only inlines NEXT_PUBLIC_* env vars into the
 * client bundle at build time.
 *
 * NEXT_PUBLIC_LINTPDF_OSS_REPO_URL is independent of the mode flag — when
 * empty the /engine page renders "coming soon"; when set to a GitHub URL
 * it renders the live repo links. This lets us flip the OSS engine to
 * "live" without a code change once the repo is published.
 */

const rawMode = process.env.NEXT_PUBLIC_ENABLE_SAAS;

if (rawMode !== "true" && rawMode !== "false") {
  throw new Error(
    `NEXT_PUBLIC_ENABLE_SAAS must be set to "true" or "false" at build time. ` +
      `Got: ${JSON.stringify(rawMode)}. ` +
      `Set it in Railway (web service env vars) or in packages/web/.env.local for dev.`,
  );
}

export type SiteMode = "saas" | "oss";

export const SITE_MODE: SiteMode = rawMode === "true" ? "saas" : "oss";

export const isSaasMode = (): boolean => SITE_MODE === "saas";
export const isOssMode = (): boolean => SITE_MODE === "oss";

const rawRepo = (process.env.NEXT_PUBLIC_LINTPDF_OSS_REPO_URL ?? "").trim();
export const OSS_REPO_URL: string | null = rawRepo === "" ? null : rawRepo;
export const ossRepoIsLive = (): boolean => OSS_REPO_URL !== null;

/**
 * Routes that are publicly indexable in OSS mode. Anything not in this
 * list still builds and renders, but is unlinked, sitemap-excluded,
 * robots-disallowed, and emits a noindex meta tag.
 */
export const OSS_PUBLIC_ROUTES = [
  "/",
  "/features",
  "/engine",
  "/about",
  "/contact",
  "/status",
  "/compliance",
] as const;

export type OssPublicRoute = (typeof OSS_PUBLIC_ROUTES)[number];

export const isPublicInOssMode = (path: string): boolean => {
  const normalized = path === "" ? "/" : path.replace(/\/+$/, "") || "/";
  return (OSS_PUBLIC_ROUTES as readonly string[]).includes(normalized);
};

/**
 * Convenience metadata fragment for hidden-in-OSS routes. Spread into a
 * page's `metadata` export so the `<meta name="robots">` tag flips
 * automatically with the mode.
 *
 *   import { hiddenInOssMetadata } from "@/lib/site-mode";
 *   export const metadata: Metadata = {
 *     title: "...",
 *     ...hiddenInOssMetadata,
 *   };
 */
export const hiddenInOssMetadata = {
  robots: isOssMode()
    ? { index: false, follow: false, nocache: true }
    : undefined,
} as const;
