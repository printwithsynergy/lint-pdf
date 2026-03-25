export const dynamic = "force-dynamic";

import { authenticateRequest } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database";
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

export async function PATCH(req: Request) {
  const cookieHeader = req.headers.get("cookie");
  const auth = await authenticateRequest(prisma, cookieHeader);

  if (!auth) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  try {
    const body = await req.json();
    const updates: Record<string, string | null> = {};

    if (typeof body.name === "string") {
      updates.name = body.name.trim() || null;
    }
    if (typeof body.avatarUrl === "string") {
      updates.avatarUrl = body.avatarUrl.trim() || null;
    }

    if (Object.keys(updates).length === 0) {
      return NextResponse.json(
        { error: "No valid fields to update" },
        { status: 400 },
      );
    }

    const updated = await prisma.user.update({
      where: { id: auth.userId },
      data: updates,
      select: { id: true, email: true, name: true, avatarUrl: true },
    });

    return NextResponse.json({ success: true, user: updated });
  } catch {
    return NextResponse.json(
      { error: "Failed to update profile" },
      { status: 500 },
    );
  }
}
