export const dynamic = "force-dynamic";

import { authenticateRequest } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { NextResponse } from "next/server";
import { parseSessionCookie } from "@/lib/auth-helpers";

// The Pixie Dust PrismaClient type doesn't know about fields the local
// LintPDF schema adds (``Tenant.engineTenantId``,
// ``Session.impersonatingTenantId``, ``AuditLog.impersonatedBy``).
// Those columns are guaranteed to exist at runtime by
// packages/app/scripts/startup.sh and the matching local Prisma
// schema in packages/app/prisma/schema/. We cast through this
// permissive alias to bridge the type gap without losing the rest of
// the typed surface.

const db = prisma as any;

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
    // Try looking up by Prisma ID first, then by engine tenant ID
    let tenant = await prisma.tenant.findUnique({
      where: { id: targetTenantId },
      select: { id: true, name: true, slug: true },
    });
    if (!tenant) {
      tenant = await db.tenant.findFirst({
        where: { engineTenantId: targetTenantId },
        select: { id: true, name: true, slug: true },
      });
    }

    if (!tenant) {
      return NextResponse.json({ error: "Tenant not found" }, { status: 404 });
    }

    // Update the session to set the impersonation target
    const sessionCookie = parseSessionCookie(cookieHeader);

    if (sessionCookie) {
      // Store the Prisma tenant ID (not the engine UUID) for session impersonation
      await db.session.updateMany({
        where: { token: sessionCookie, userId: user.id },
        data: { impersonatingTenantId: tenant.id },
      });
    }

    // Audit log
    await prisma.auditLog.create({
      data: {
        tenantId: tenant.id,
        userId: user.id,
        action: "admin.impersonation.started",
        entity: "Tenant",
        entityId: tenant.id,
        metadata: { tenantName: tenant.name, impersonatedBy: user.id },
      },
    });

    return NextResponse.json({
      impersonating: true,
      tenant: { id: tenant.id, name: tenant.name, slug: tenant.slug },
    });
  }

  // Stop impersonation
  const sessionCookie = parseSessionCookie(cookieHeader);

  if (sessionCookie) {
    // Get current impersonation target for audit log
    const session = await db.session.findUnique({
      where: { token: sessionCookie },
      select: { impersonatingTenantId: true },
    });

    await db.session.updateMany({
      where: { token: sessionCookie, userId: user.id },
      data: { impersonatingTenantId: null },
    });

    if (session?.impersonatingTenantId) {
      await db.auditLog.create({
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

  const sessionCookie = parseSessionCookie(cookieHeader);

  if (!sessionCookie) {
    return NextResponse.json({ impersonating: false, tenant: null });
  }

  const session = await db.session.findUnique({
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
