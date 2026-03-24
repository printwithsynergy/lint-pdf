import { authenticateRequest } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database";
import { NextResponse } from "next/server";

/**
 * Verify the request is from a super admin.
 * Returns null if authorized, or a NextResponse error to return immediately.
 */
export async function requireSuperAdmin(
  req: Request,
): Promise<NextResponse | null> {
  const cookieHeader = req.headers.get("cookie");
  const auth = await authenticateRequest(prisma, cookieHeader);

  if (!auth) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const user = await prisma.user.findUnique({
    where: { id: auth.userId },
    select: { isSuperAdmin: true },
  });

  if (!user?.isSuperAdmin) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  return null;
}
