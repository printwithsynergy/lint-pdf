export const dynamic = "force-dynamic";

import { authenticateRequest } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database";
import { NextResponse } from "next/server";

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
    const { getCookieName } = await import("@thinkneverland/pixie-dust-config");
    const cookieName = getCookieName();
    const cookies = cookieHeader?.split(";").map((c: string) => c.trim()) ?? [];
    const sessionToken = cookies
      .find((c: string) => c.startsWith(`${cookieName}=`))
      ?.split("=")[1];

    if (sessionToken) {
      const session = await prisma.session.findUnique({
        where: { token: sessionToken },
        select: { impersonatingTenantId: true },
      });

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
