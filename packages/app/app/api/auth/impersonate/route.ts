export const dynamic = "force-dynamic";

import { authenticateRequest } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { NextResponse } from "next/server";
import { parseSessionCookie } from "@/lib/auth-helpers";

// The Pixie Dust PrismaClient bundled in
// ``@thinkneverland/pixie-dust-database/server`` doesn't know about the
// fields the local LintPDF schema adds:
//   * ``Tenant.engineTenantId``
//   * ``Session.impersonatingTenantId``
//   * ``AuditLog.impersonatedBy``
// The columns themselves are guaranteed to exist in Postgres at
// runtime by ``packages/app/scripts/startup.sh``. Typed calls that
// reference those fields throw ``PrismaClientValidationError`` before
// ever hitting the database — so every impersonation-related query in
// this file goes through ``$queryRaw`` / ``$executeRaw``, bypassing
// the client's field validator.

/**
 * POST /api/auth/impersonate
 *
 * Allows a super admin to start "assisting" a customer tenant.
 * This is NOT true impersonation — the session still belongs to the super admin,
 * and all audit logs record the super admin's real user ID plus an
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

  if (targetTenantId) {
    // Try Prisma ID first, then the engine-tenant-id fallback. Both go
    // through raw SQL because the latter references ``engineTenantId``
    // which the bundled client doesn't know about, and keeping the
    // two lookups symmetric is simpler than mixing typed + raw here.
    const byId = await prisma.$queryRaw<
      { id: string; name: string; slug: string }[]
    >`SELECT id, name, slug FROM "Tenant" WHERE id = ${targetTenantId} LIMIT 1`;
    let tenant = byId[0] ?? null;
    if (!tenant) {
      const byEngine = await prisma.$queryRaw<
        { id: string; name: string; slug: string }[]
      >`SELECT id, name, slug FROM "Tenant" WHERE "engineTenantId" = ${targetTenantId} LIMIT 1`;
      tenant = byEngine[0] ?? null;
    }

    if (!tenant) {
      return NextResponse.json({ error: "Tenant not found" }, { status: 404 });
    }

    const sessionCookie = parseSessionCookie(cookieHeader);

    if (sessionCookie) {
      await prisma.$executeRaw`
        UPDATE "Session"
        SET "impersonatingTenantId" = ${tenant.id}
        WHERE token = ${sessionCookie} AND "userId" = ${user.id}
      `;
    }

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
    const rows = await prisma.$queryRaw<
      { impersonatingTenantId: string | null }[]
    >`SELECT "impersonatingTenantId" FROM "Session" WHERE token = ${sessionCookie} LIMIT 1`;
    const previousTargetId = rows[0]?.impersonatingTenantId ?? null;

    await prisma.$executeRaw`
      UPDATE "Session"
      SET "impersonatingTenantId" = NULL
      WHERE token = ${sessionCookie} AND "userId" = ${user.id}
    `;

    if (previousTargetId) {
      // AuditLog.impersonatedBy is a local-schema column the bundled
      // client doesn't know about, so write via raw SQL.
      const auditId = randomId();
      await prisma.$executeRaw`
        INSERT INTO "AuditLog"
          (id, "tenantId", "userId", action, entity, "entityId", metadata,
           "impersonatedBy", "createdAt")
        VALUES
          (${auditId}, ${previousTargetId}, ${user.id},
           ${"admin.impersonation.ended"}, ${"Tenant"}, ${previousTargetId},
           '{}'::jsonb, ${user.id}, NOW())
      `;
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

  const rows = await prisma.$queryRaw<
    { impersonatingTenantId: string | null }[]
  >`SELECT "impersonatingTenantId" FROM "Session" WHERE token = ${sessionCookie} LIMIT 1`;
  const impersonatingTenantId = rows[0]?.impersonatingTenantId ?? null;

  if (!impersonatingTenantId) {
    return NextResponse.json({ impersonating: false, tenant: null });
  }

  const tenant = await prisma.tenant.findUnique({
    where: { id: impersonatingTenantId },
    select: { id: true, name: true, slug: true },
  });

  return NextResponse.json({
    impersonating: true,
    tenant,
  });
}

/** cuid-ish random id suitable for the AuditLog pk column.
 *
 * The table's default is ``cuid()`` via Prisma; when we insert with raw
 * SQL the default doesn't run, so mint an id here. Uses
 * ``crypto.getRandomValues`` so the id is unpredictable and short enough
 * to fit the existing column (no length constraint, but historically
 * cuids are ~25 chars).
 */
function randomId(): string {
  const bytes = new Uint8Array(16);
  globalThis.crypto.getRandomValues(bytes);
  const alphabet = "0123456789abcdefghijklmnopqrstuvwxyz";
  let s = "c";
  for (const b of bytes) {
    // eslint-disable-next-line security/detect-object-injection
    s += alphabet[b % alphabet.length];
  }
  return s;
}
