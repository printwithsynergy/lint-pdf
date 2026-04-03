export const dynamic = "force-dynamic";

import {
  verifyMagicLinkCode,
  createSession,
} from "@thinkneverland/pixie-dust-auth";
import {
  getCookieName,
  getCookieOptions,
  env,
} from "@thinkneverland/pixie-dust-config";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { z } from "zod";
import { getClientInfo } from "@/lib/auth-helpers";

const verifySchema = z.object({
  email: z.string().email(),
  code: z.string().length(6),
});

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const parsed = verifySchema.safeParse(body);

    if (!parsed.success) {
      return NextResponse.json({ error: "Invalid input." }, { status: 400 });
    }

    const { email, code } = parsed.data;
    const result = await verifyMagicLinkCode(prisma, email, code);

    if ("error" in result) {
      return NextResponse.json({ error: result.error }, { status: 400 });
    }

    const session = await createSession(prisma, result.userId, getClientInfo(req));

    const cookieStore = await cookies();
    cookieStore.set(getCookieName(), session.token, {
      ...getCookieOptions(),
      secure: env.NODE_ENV === "production",
    });

    return NextResponse.json({ success: true, redirect: "/dashboard" });
  } catch {
    return NextResponse.json(
      { error: "Verification failed." },
      { status: 500 },
    );
  }
}
