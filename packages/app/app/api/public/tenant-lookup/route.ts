export const dynamic = "force-dynamic";

import { getBranding } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { NextResponse } from "next/server";

/**
 * Public tenant lookup for the desktop and mobile apps' first-run
 * Onboarding screen. The user types a tenant name, slug, id, or
 * custom domain; this endpoint resolves it and returns the matching
 * tenant plus the AppSettings branding blob the app should apply
 * as a theme.
 *
 * Public on purpose — both apps need to call this *before* any user
 * has authenticated. The Pixie Dust middleware rate-limits the path
 * automatically (it isn't in `rateLimitExemptPaths`), so we don't
 * need bespoke throttling here.
 */

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: corsHeaders });
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const q = url.searchParams.get("q")?.trim();
  if (!q) {
    return NextResponse.json(
      { error: "Missing required query parameter 'q'." },
      { status: 400, headers: corsHeaders },
    );
  }
  if (q.length > 200) {
    return NextResponse.json(
      { error: "Query parameter 'q' is too long." },
      { status: 400, headers: corsHeaders },
    );
  }

  const lower = q.toLowerCase();

  // Prefer unique-key matches (id, slug, domain) before falling back
  // to name. Name is not unique on the Tenant model, so a name-only
  // match could be ambiguous — exact id/slug/domain wins when possible.
  const tenant =
    (await prisma.tenant.findFirst({
      where: {
        status: "ACTIVE",
        OR: [{ id: q }, { slug: lower }, { domain: lower }],
      },
      select: { id: true, name: true, slug: true, domain: true },
    })) ??
    (await prisma.tenant.findFirst({
      where: {
        status: "ACTIVE",
        name: { equals: q, mode: "insensitive" },
      },
      orderBy: { createdAt: "asc" },
      select: { id: true, name: true, slug: true, domain: true },
    }));

  if (!tenant) {
    return NextResponse.json(
      { error: "Tenant not found" },
      { status: 404, headers: corsHeaders },
    );
  }

  const branding = await getBranding(prisma);

  return NextResponse.json(
    {
      tenantId: tenant.id,
      name: tenant.name,
      slug: tenant.slug,
      domain: tenant.domain,
      branding,
    },
    { headers: corsHeaders },
  );
}
