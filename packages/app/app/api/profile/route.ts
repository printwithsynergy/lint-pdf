export const dynamic = "force-dynamic";

import { authenticateRequest } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { NextResponse } from "next/server";

/**
 * GET / POST /api/profile — user-facing profile API consumed by
 * Pixie Dust's upstream ProfilePage (rendered at /dashboard/profile).
 *
 * Without these handlers the upstream component fetches `/api/profile`
 * and 404s, then hangs on `waitUntil: networkidle` because the failed
 * request never resolves. Same gotcha as `/api/team`.
 */

export async function GET(req: Request) {
  const auth = await authenticateRequest(prisma, req.headers.get("cookie"));
  if (!auth) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }
  const user = await prisma.user.findUnique({
    where: { id: auth.userId },
    select: { id: true, email: true, name: true, avatarUrl: true },
  });
  if (!user) {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }
  return NextResponse.json(user);
}

export async function POST(req: Request) {
  const auth = await authenticateRequest(prisma, req.headers.get("cookie"));
  if (!auth) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  const updates: { name?: string | null; avatarUrl?: string | null } = {};
  if (typeof body.name === "string") updates.name = body.name.trim() || null;
  if (typeof body.avatarUrl === "string")
    updates.avatarUrl = body.avatarUrl.trim() || null;

  const user = await prisma.user.update({
    where: { id: auth.userId },
    data: updates,
    select: { id: true, email: true, name: true, avatarUrl: true },
  });
  return NextResponse.json(user);
}
