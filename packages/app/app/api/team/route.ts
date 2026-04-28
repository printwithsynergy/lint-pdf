export const dynamic = "force-dynamic";

import { authenticateRequest } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { NextResponse } from "next/server";

/**
 * GET /api/team — list members of the caller's primary tenant.
 *
 * The Pixie Dust dashboard's TeamPage hard-fetches /api/team + /api/team/invites.
 * Without this route the page hangs at networkidle (404 + 404). Returns the
 * `{ id, role, joinedAt, user }` shape the upstream component expects.
 */
export async function GET(req: Request) {
  const auth = await authenticateRequest(prisma, req.headers.get("cookie"));
  if (!auth) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }

  // Prefer the user's first tenant — TeamPage doesn't expose a tenant picker.
  const membership = await prisma.tenantUser.findFirst({
    where: { userId: auth.userId },
    orderBy: { joinedAt: "asc" },
    select: { tenantId: true },
  });

  if (!membership) {
    // No tenant yet — return an empty list rather than 404 so the page renders.
    return NextResponse.json([]);
  }

  const members = await prisma.tenantUser.findMany({
    where: { tenantId: membership.tenantId },
    include: {
      user: {
        select: { id: true, email: true, name: true, avatarUrl: true },
      },
    },
    orderBy: { joinedAt: "asc" },
  });

  return NextResponse.json(
    members.map((m) => ({
      id: m.id,
      role: m.role,
      joinedAt: m.joinedAt,
      user: {
        id: m.user.id,
        email: m.user.email,
        name: m.user.name,
        avatarUrl: m.user.avatarUrl,
      },
    })),
  );
}
