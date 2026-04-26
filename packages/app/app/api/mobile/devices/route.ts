export const dynamic = "force-dynamic";

import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { NextResponse } from "next/server";
import { z } from "zod";

import {
  requireMobileUser,
  requireTenantMembership,
} from "@/lib/mobile-auth";

/**
 * POST /api/mobile/devices — register or refresh a push-notification
 * device token for the authenticated user under the captured tenant.
 *
 * The mobile app calls this once per launch (or once per FCM/APNs
 * token rotation). Upserting on `pushToken` keeps the table small
 * and lets `lastSeenAt` track the most recent activity for stale-
 * device pruning later.
 *
 * Auth: Pixie Dust session cookie. The "MobileDevice" table is
 * managed at the LintPDF tier (Prisma schema lives in
 * `prisma/schema/base.prisma`, raw-SQL fallback in
 * `scripts/startup.sh`), but isn't part of the bundled Pixie Dust
 * client — so persistence runs through `$executeRaw` /
 * `$queryRaw` rather than `prisma.mobileDevice`. Same pattern as
 * the `Annotation` and `ReportView` tables.
 */

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Cookie",
  "Access-Control-Allow-Credentials": "true",
};

const requestSchema = z.object({
  pushToken: z.string().min(8).max(4096),
  platform: z.enum(["ios", "android"]),
  tenantId: z.string().min(1),
});

interface MobileDeviceRow {
  id: string;
  platform: string;
  createdAt: Date;
  lastSeenAt: Date;
}

function newCuidLike(): string {
  // Cheap collision-resistant id matching the Prisma `cuid()` shape
  // closely enough for our purposes (`c` + 24 hex chars). The
  // `MobileDevice` table's primary key only needs to be unique;
  // we never expose the id externally beyond the same response.
  const rand = Array.from(crypto.getRandomValues(new Uint8Array(12)))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return `c${rand}`;
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: corsHeaders });
}

export async function POST(req: Request) {
  const auth = await requireMobileUser(req);
  if (auth instanceof NextResponse) return auth;

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON body." },
      { status: 400, headers: corsHeaders },
    );
  }

  const parsed = requestSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { error: parsed.error.issues[0]?.message ?? "Invalid input." },
      { status: 400, headers: corsHeaders },
    );
  }
  const { pushToken, platform, tenantId } = parsed.data;

  const denied = await requireTenantMembership(auth.userId, tenantId);
  if (denied) return denied;

  const id = newCuidLike();

  await prisma.$executeRaw`
    INSERT INTO "MobileDevice" ("id", "userId", "tenantId", "platform", "pushToken", "createdAt", "lastSeenAt")
    VALUES (${id}, ${auth.userId}, ${tenantId}, ${platform}, ${pushToken}, NOW(), NOW())
    ON CONFLICT ("pushToken") DO UPDATE SET
      "userId" = EXCLUDED."userId",
      "tenantId" = EXCLUDED."tenantId",
      "platform" = EXCLUDED."platform",
      "lastSeenAt" = NOW()
  `;

  const rows = await prisma.$queryRaw<MobileDeviceRow[]>`
    SELECT "id", "platform", "createdAt", "lastSeenAt"
      FROM "MobileDevice"
     WHERE "pushToken" = ${pushToken}
     LIMIT 1
  `;

  if (rows.length === 0) {
    // Should never happen — upsert just succeeded — but guard
    // anyway so a stale connection doesn't silently 200 with junk.
    return NextResponse.json(
      { error: "Failed to read back device row after upsert." },
      { status: 500, headers: corsHeaders },
    );
  }

  return NextResponse.json(rows[0], {
    status: 200,
    headers: corsHeaders,
  });
}
