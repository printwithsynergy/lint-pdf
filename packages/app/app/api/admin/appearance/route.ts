export const dynamic = "force-dynamic";

import { authenticateRequest } from "@thinkneverland/pixie-dust-auth";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { NextResponse } from "next/server";

/**
 * GET / POST /api/admin/appearance — admin-scoped appearance config
 * (singleton AppSettings.customCss + themeTokenOverrides). Pixie
 * Dust's upstream AppearancePage hits this with `scope="platform"`.
 */
export async function GET(req: Request) {
  const auth = await authenticateRequest(prisma, req.headers.get("cookie"));
  if (!auth) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }
  const user = await prisma.user.findUnique({
    where: { id: auth.userId },
    select: { isSuperAdmin: true },
  });
  if (!user?.isSuperAdmin) {
    return NextResponse.json({ error: "forbidden" }, { status: 403 });
  }
  const settings = await prisma.appSettings.findUnique({
    where: { id: "singleton" },
    select: { customCss: true },
  });
  // themeTokenOverrides isn't a column on AppSettings — surface a
  // null so the upstream AppearancePage renders its empty state and
  // the form still works.
  return NextResponse.json({
    customCss: settings?.customCss ?? null,
    themeTokenOverrides: null,
  });
}

export async function POST(req: Request) {
  const auth = await authenticateRequest(prisma, req.headers.get("cookie"));
  if (!auth) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }
  const user = await prisma.user.findUnique({
    where: { id: auth.userId },
    select: { isSuperAdmin: true },
  });
  if (!user?.isSuperAdmin) {
    return NextResponse.json({ error: "forbidden" }, { status: 403 });
  }
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  const customCss =
    typeof body.customCss === "string" ? body.customCss : null;

  await prisma.appSettings.upsert({
    where: { id: "singleton" },
    create: { id: "singleton", customCss },
    update: { customCss },
  });
  return NextResponse.json({ customCss, themeTokenOverrides: null });
}
