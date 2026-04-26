import { authenticateRequest } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { NextResponse } from "next/server";

export interface MobileAuthSuccess {
  userId: string;
  email: string;
}

/**
 * Authenticate a request from the LintPDF mobile companion app via
 * the standard Pixie Dust session cookie. Returns either the
 * resolved user identity or a NextResponse error to short-circuit.
 *
 * Note: this only verifies the session — tenant membership is
 * validated separately by the caller against the `tenantId` they
 * receive from the request, because users can belong to multiple
 * tenants and the mobile app picks one at Onboarding time.
 */
export async function requireMobileUser(
  req: Request,
): Promise<MobileAuthSuccess | NextResponse> {
  const cookieHeader = req.headers.get("cookie");
  const auth = await authenticateRequest(prisma, cookieHeader);
  if (!auth) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }
  return { userId: auth.userId, email: auth.email };
}

/**
 * Confirm the authenticated user is a member of the given tenant.
 * Returns null on success, a NextResponse 403 on miss.
 */
export async function requireTenantMembership(
  userId: string,
  tenantId: string,
): Promise<NextResponse | null> {
  const link = await prisma.tenantUser.findFirst({
    where: { userId, tenantId },
    select: { id: true },
  });
  if (!link) {
    return NextResponse.json(
      { error: "User is not a member of the requested tenant." },
      { status: 403 },
    );
  }
  return null;
}
