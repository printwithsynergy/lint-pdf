export const dynamic = "force-dynamic";

import {
  verifyMagicLink,
  createSession,
  getResolvedBranding,
  renderVerifiedPageHtml,
} from "@thinkneverland/pixie-dust-auth";
import {
  getCookieName,
  getCookieOptions,
  env,
} from "@thinkneverland/pixie-dust-config";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { getClientInfo } from "@/lib/auth-helpers";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const token = url.searchParams.get("token");

  if (!token) {
    return NextResponse.redirect(
      `${env.APP_URL}/auth/login?error=missing_token`,
    );
  }

  const result = await verifyMagicLink(prisma, token);

  if ("error" in result) {
    return NextResponse.redirect(
      `${env.APP_URL}/auth/login?error=${encodeURIComponent(result.error)}`,
    );
  }

  const session = await createSession(prisma, result.userId, getClientInfo(req));

  const cookieStore = await cookies();
  cookieStore.set(getCookieName(), session.token, {
    ...getCookieOptions(),
    secure: env.NODE_ENV === "production",
  });

  // Render the branded verified page via the shared Pixie Dust helper
  // so logo, palette, tagline, and footer stay in lock-step with the
  // admin branding panel. Previous LintPDF-local implementation
  // hardcoded #0a0a0a / #111 colors and referenced /logo-dark.svg
  // which produced an unbranded black page with a broken logo.
  const branding = await getResolvedBranding(prisma);
  return new NextResponse(
    renderVerifiedPageHtml({ branding, appUrl: env.APP_URL }),
    {
      status: 200,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    },
  );
}
