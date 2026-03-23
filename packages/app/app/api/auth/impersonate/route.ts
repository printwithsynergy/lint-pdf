export const dynamic = "force-dynamic";

import { authenticateRequest } from "@thinkneverland/pixie-dust-auth";
import { getCookieName } from "@thinkneverland/pixie-dust-config";
import { prisma } from "@thinkneverland/pixie-dust-database";
import { NextResponse } from "next/server";

/**
 * POST /api/auth/impersonate
 *
 * Allows a super admin to start "assisting" a customer tenant.
 * This is NOT true impersonation — the session still belongs to the super admin,
 * and all audit logs will record the super admin's real user ID plus an
 * `impersonatedBy` marker.
 *
 * Body: { tenantId: string } — the tenant to assist
 *       OR { tenantId: null } — stop assisting (return to own view)
 */
export async function POST(req: Request) {
  const cookieHeader = req.headers.get("cookie");
  const auth = await authenticateRequest(prisma, cookieHeader);

  if (!auth) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  // Verify the user is a super admin
  const user = await prisma.user.findUnique({
    where: { id: auth.userId },
    select: { id: true, isSuperAdmin: true },
  });

  if (!user?.isSuperAdmin) {
    return NextResponse.json(
      { error: "Only super admins can assist customer tenants" },
      { status: 403 },
    );
  }

  const body = await req.json();
  const targetTenantId: string | null = body.tenantId ?? null;

  // Validate the target tenant exists (if starting impersonation)
  if (targetTenantId) {
    const tenant = await prisma.tenant.findUnique({
      where: { id: targetTenantId },
      select: { id: true, name: true, slug: true },
    });

    if (!tenant) {
      return NextResponse.json(
        { error: "Tenant not found" },
        { status: 404 },
      );
    }

    // Update the session to set the impersonation target
    const cookieName = getCookieName();
    const cookies = cookieHeader?.split(";").map((c) => c.trim()) ?? [];
    const sessionCookie = cookies
      .find((c) => c.startsWith(`${cookieName}=`))
      ?.split("=")[1];

    if (sessionCookie) {
      await prisma.session.updateMany({
        where: { token: sessionCookie, userId: user.id },
        data: { impersonatingTenantId: targetTenantId },
      });
    }

    // Audit log
    await prisma.auditLog.create({
      data: {
        tenantId: targetTenantId,
        userId: user.id,
        action: "admin.impersonation.started",
        entity: "Tenant",
        entityId: targetTenantId,
        impersonatedBy: user.id,
        metadata: { tenantName: tenant.name },
      },
    });

    return NextResponse.json({
      impersonating: true,
      tenant: { id: tenant.id, name: tenant.name, slug: tenant.slug },
    });
  }

  // Stop impersonation
  const cookieName = getCookieName();
  const cookies = cookieHeader?.split(";").map((c) => c.trim()) ?? [];
  const sessionCookie = cookies
    .find((c) => c.startsWith(`${cookieName}=`))
    ?.split("=")[1];

  if (sessionCookie) {
    // Get current impersonation target for audit log
    const session = await prisma.session.findUnique({
      where: { token: sessionCookie },
      select: { impersonatingTenantId: true },
    });

    await prisma.session.updateMany({
      where: { token: sessionCookie, userId: user.id },
      data: { impersonatingTenantId: null },
    });

    if (session?.impersonatingTenantId) {
      await prisma.auditLog.create({
        data: {
          tenantId: session.impersonatingTenantId,
          userId: user.id,
          action: "admin.impersonation.ended",
          entity: "Tenant",
          entityId: session.impersonatingTenantId,
          impersonatedBy: user.id,
        },
      });
    }
  }

  return NextResponse.json({ impersonating: false, tenant: null });
}

/**
 * GET /api/auth/impersonate
 *
 * Returns the current impersonation state for the session.
 */
export async function GET(req: Request) {
  const cookieHeader = req.headers.get("cookie");
  const auth = await authenticateRequest(prisma, cookieHeader);

  if (!auth) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const user = await prisma.user.findUnique({
    where: { id: auth.userId },
    select: { id: true, isSuperAdmin: true },
  });

  if (!user?.isSuperAdmin) {
    return NextResponse.json({ impersonating: false, tenant: null });
  }

  const cookieName = getCookieName();
  const cookies = cookieHeader?.split(";").map((c) => c.trim()) ?? [];
  const sessionCookie = cookies
    .find((c) => c.startsWith(`${cookieName}=`))
    ?.split("=")[1];

  if (!sessionCookie) {
    return NextResponse.json({ impersonating: false, tenant: null });
  }

  const session = await prisma.session.findUnique({
    where: { token: sessionCookie },
    select: { impersonatingTenantId: true },
  });

  if (!session?.impersonatingTenantId) {
    return NextResponse.json({ impersonating: false, tenant: null });
  }

  const tenant = await prisma.tenant.findUnique({
    where: { id: session.impersonatingTenantId },
    select: { id: true, name: true, slug: true },
  });

  return NextResponse.json({
    impersonating: true,
    tenant,
  });
}
