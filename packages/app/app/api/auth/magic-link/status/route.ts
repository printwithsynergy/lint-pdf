export const dynamic = "force-dynamic";

import { checkMagicLinkStatus } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const pollingToken = url.searchParams.get("pollingToken");

  if (!pollingToken) {
    return NextResponse.json({ verified: false }, { status: 400 });
  }

  const result = await checkMagicLinkStatus(prisma, pollingToken);

  if (!result.verified) {
    return NextResponse.json({ verified: false });
  }

  return NextResponse.json({ verified: true });
}
