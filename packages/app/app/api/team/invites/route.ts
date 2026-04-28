export const dynamic = "force-dynamic";

import { authenticateRequest } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { NextResponse } from "next/server";

/**
 * GET /api/team/invites — pending (non-revoked, non-accepted) invites
 * for the caller's primary tenant. Mirrors the shape Pixie Dust's
 * upstream TeamPage expects.
 */
export async function GET(req: Request) {
  const auth = await authenticateRequest(prisma, req.headers.get("cookie"));
  if (!auth) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }

  const membership = await prisma.tenantUser.findFirst({
    where: { userId: auth.userId },
    orderBy: { joinedAt: "asc" },
    select: { tenantId: true },
  });

  if (!membership) {
    return NextResponse.json([]);
  }

  // The bundled Pixie Dust PrismaClient doesn't know about
  // `acceptedAt` / `revokedAt` columns the local schema adds (same
  // gotcha as Session.impersonatingTenantId — see /api/auth/me).
  // Drop to raw SQL so the field validator doesn't throw.
  const invites = await prisma.$queryRaw<
    {
      id: string;
      email: string;
      role: string;
      expiresAt: Date;
    }[]
  >`SELECT id, email, role, "expiresAt"
    FROM "TenantInvite"
    WHERE "tenantId" = ${membership.tenantId}
      AND "acceptedAt" IS NULL
      AND "revokedAt" IS NULL
    ORDER BY "createdAt" DESC`;

  return NextResponse.json(
    invites.map((i) => ({
      id: i.id,
      email: i.email,
      role: i.role,
      expiresAt: i.expiresAt,
    })),
  );
}
