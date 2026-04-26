export const dynamic = "force-dynamic";

import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { NextResponse } from "next/server";

import { requireMobileUser } from "@/lib/mobile-auth";

/**
 * DELETE /api/mobile/devices/{pushToken} — unregister a device.
 * Called on sign-out so the engine's approval webhook handler stops
 * sending push to a stale token.
 *
 * Authorization is intentionally loose-but-safe: the caller must be
 * authenticated and the row must belong to them. We don't 404 a
 * non-existent token — the mobile app might call DELETE
 * speculatively after signing out, and the row may already have
 * been pruned. Idempotent succeed-on-no-op keeps the client logic
 * simple.
 *
 * Persistence runs through `$executeRaw` because `MobileDevice`
 * isn't part of the bundled Pixie Dust client (same pattern as
 * `Annotation` and `ReportView`).
 */

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Cookie",
  "Access-Control-Allow-Credentials": "true",
};

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: corsHeaders });
}

export async function DELETE(
  req: Request,
  ctx: { params: Promise<{ pushToken: string }> },
) {
  const auth = await requireMobileUser(req);
  if (auth instanceof NextResponse) return auth;

  const { pushToken } = await ctx.params;
  if (!pushToken) {
    return NextResponse.json(
      { error: "Missing pushToken in URL." },
      { status: 400, headers: corsHeaders },
    );
  }

  await prisma.$executeRaw`
    DELETE FROM "MobileDevice"
     WHERE "pushToken" = ${pushToken}
       AND "userId" = ${auth.userId}
  `;

  return NextResponse.json({ ok: true }, { status: 200, headers: corsHeaders });
}
