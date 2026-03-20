export const dynamic = "force-dynamic";

import { destroySession } from "@thinkneverland/pixie-dust-auth";
import { getCookieName, env } from "@thinkneverland/pixie-dust-config";
import { prisma } from "@thinkneverland/pixie-dust-database";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export async function POST() {
  const cookieStore = await cookies();
  const token = cookieStore.get(getCookieName())?.value;

  if (token) {
    await destroySession(prisma, token);
  }

  cookieStore.delete(getCookieName());

  return NextResponse.redirect(`${env.APP_URL}/auth/login`);
}

export async function GET() {
  return POST();
}
