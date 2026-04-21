export const dynamic = "force-dynamic";

import { authenticateRequest } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { NextResponse } from "next/server";
import { parseSessionCookie } from "@/lib/auth-helpers";

export async function GET(req: Request) {
  const cookieHeader = req.headers.get("cookie");
  const auth = await authenticateRequest(prisma, cookieHeader);

  if (!auth) {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }

  const user = await prisma.user.findUnique({
    where: { id: auth.userId },
    select: {
      id: true,
      email: true,
      name: true,
      avatarUrl: true,
      isSuperAdmin: true,
      createdAt: true,
    },
  });

  if (!user) {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }

  const tenants = await prisma.tenantUser.findMany({
    where: { userId: user.id },
    include: {
      tenant: { select: { id: true, name: true, slug: true, status: true } },
    },
    orderBy: { joinedAt: "asc" },
  });

  // Check impersonation state for super admins
  let impersonating: {
    tenantId: string;
    tenantName: string;
    tenantSlug: string;
  } | null = null;
  if (user.isSuperAdmin) {
    const sessionToken = parseSessionCookie(cookieHeader);

    if (sessionToken) {
      // ``impersonatingTenantId`` lives in the local Prisma schema
      // (packages/app/prisma/schema/base.prisma) but the Pixie Dust
      // PrismaClient bundled in ``@thinkneverland/pixie-dust-database/server``
      // doesn't know about the column — typed calls fail at runtime
      // with ``PrismaClientValidationError: Unknown field
      // 'impersonatingTenantId'``. The column itself is guaranteed to
      // exist in Postgres by ``packages/app/scripts/startup.sh``; using
      // ``$queryRaw`` bypasses the client's field validator and goes
      // straight to the database.
      const rows = await prisma.$queryRaw<
        { impersonatingTenantId: string | null }[]
      >`SELECT "impersonatingTenantId" FROM "Session" WHERE token = ${sessionToken} LIMIT 1`;
      const session = rows[0] ?? null;

      if (session?.impersonatingTenantId) {
        const targetTenant = await prisma.tenant.findUnique({
          where: { id: session.impersonatingTenantId },
          select: { id: true, name: true, slug: true },
        });
        if (targetTenant) {
          impersonating = {
            tenantId: targetTenant.id,
            tenantName: targetTenant.name,
            tenantSlug: targetTenant.slug,
          };
        }
      }
    }
  }

  return NextResponse.json({
    authenticated: true,
    user: {
      ...user,
      tenants: tenants.map((t: (typeof tenants)[number]) => ({
        id: t.tenant.id,
        name: t.tenant.name,
        slug: t.tenant.slug,
        status: t.tenant.status,
        role: t.role,
      })),
    },
    impersonating,
  });
}
