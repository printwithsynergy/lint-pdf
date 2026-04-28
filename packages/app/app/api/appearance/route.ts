export const dynamic = "force-dynamic";

import { authenticateRequest } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { NextResponse } from "next/server";

/**
 * GET / POST /api/appearance — tenant-scoped appearance config.
 * Pixie Dust's upstream AppearancePage hits this with `scope="tenant"`.
 *
 * The local schema does not yet have a TenantAppearance model.
 * Returns null defaults so the page renders cleanly; POST is a
 * no-op until per-tenant theming lands.
 */
export async function GET(req: Request) {
  const auth = await authenticateRequest(prisma, req.headers.get("cookie"));
  if (!auth) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }
  return NextResponse.json({
    customCss: null,
    themeTokenOverrides: null,
  });
}

export async function POST(req: Request) {
  const auth = await authenticateRequest(prisma, req.headers.get("cookie"));
  if (!auth) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }
  // No-op stub: persistence requires a TenantAppearance schema row
  // that doesn't exist yet. Returning 200 keeps the dashboard form
  // submit flow intact; a follow-up PR can wire real per-tenant
  // appearance overrides once the schema lands.
  return NextResponse.json({ customCss: null, themeTokenOverrides: null });
}
