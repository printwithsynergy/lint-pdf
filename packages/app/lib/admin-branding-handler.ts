/**
 * Admin branding API handler — shared by the several possible URLs
 * Pixie Dust's `BrandingPage` component may PATCH / GET from.
 *
 * The site-wide `AppSettings` row is a singleton managed by Pixie Dust. This
 * page backs the `/dashboard/admin/branding` route. Only SUPER_ADMINs are
 * allowed to read or write it.
 *
 * Why several paths? `BrandingPage` from `@thinkneverland/pixie-dust-dashboard`
 * ships compiled — we can't read the fetch URL it uses. Registering this
 * handler at the obvious candidates (`/api/admin/branding`, `/api/auth/branding`,
 * `/api/branding`) means whichever convention the package picks will resolve.
 */
import { getBranding } from "@thinkneverland/pixie-dust-auth";
import { updateBranding } from "@thinkneverland/pixie-dust-auth/server";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { NextResponse } from "next/server";

import { requireSuperAdmin } from "@/lib/admin-auth";

/**
 * Fields on `AppSettings` that Pixie Dust's `BrandingPage` knows about.
 * Mirrors the schema at `prisma/schema/base.prisma` lines 162-190.
 */
const ALLOWED_FIELDS = [
  "brandName",
  "brandLogoUrl",
  "brandLogoUrlDark",
  "brandTagline",
  "customCss",
  "primaryColor",
  "accentColor",
  "emailButtonColor",
  "loginBgColor",
  "loginCardColor",
  "loginTextColor",
  "loginInputColor",
  "loginRingColor",
  "loginBgColorDark",
  "loginCardColorDark",
  "loginTextColorDark",
  "loginInputColorDark",
  "loginRingColorDark",
  "sidebarBgColor",
  "sidebarTextColor",
  "sidebarAccentColor",
  "faviconUrl",
  "loginHeading",
  "loginSubheading",
  "disabledPlugins",
] as const;

type AllowedField = (typeof ALLOWED_FIELDS)[number];

function pickAllowed(
  input: Record<string, unknown>,
): Partial<Record<AllowedField, unknown>> {
  const out: Partial<Record<AllowedField, unknown>> = {};
  for (const key of ALLOWED_FIELDS) {
    if (key in input) out[key] = input[key];
  }
  return out;
}

/**
 * GET handler — returns the current AppSettings for the BrandingPage to hydrate.
 */
export async function handleGet(req: Request): Promise<NextResponse> {
  const denied = await requireSuperAdmin(req);
  if (denied) return denied;

  try {
    const branding = await getBranding(prisma);
    return NextResponse.json(branding);
  } catch (e) {
    return NextResponse.json(
      {
        error: "Failed to load branding",
        detail: e instanceof Error ? e.message : String(e),
      },
      { status: 500 },
    );
  }
}

/**
 * PATCH handler — writes the submitted branding fields to AppSettings via
 * Pixie Dust's `updateBranding()`.
 */
export async function handlePatch(req: Request): Promise<NextResponse> {
  const denied = await requireSuperAdmin(req);
  if (denied) return denied;

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Malformed JSON body" }, { status: 400 });
  }
  if (!body || typeof body !== "object") {
    return NextResponse.json({ error: "Expected JSON object" }, { status: 400 });
  }

  const data = pickAllowed(body as Record<string, unknown>);

  try {
    // `updateBranding()` from pixie-dust-auth/server upserts the singleton
    // AppSettings row — safe to call with a partial field set.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const updated = await updateBranding(prisma, data as any);
    return NextResponse.json(updated);
  } catch (e) {
    return NextResponse.json(
      {
        error: "Failed to save branding",
        detail: e instanceof Error ? e.message : String(e),
      },
      { status: 500 },
    );
  }
}

/**
 * POST handler — accept as an alias for PATCH so BrandingPage can use either.
 */
export const handlePost = handlePatch;

/**
 * PUT handler — accept as an alias for PATCH so BrandingPage can use either.
 */
export const handlePut = handlePatch;
