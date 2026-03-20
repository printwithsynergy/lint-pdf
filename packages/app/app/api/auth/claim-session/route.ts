export const dynamic = "force-dynamic";

import {
  checkMagicLinkStatus,
  createSession,
} from "@thinkneverland/pixie-dust-auth";
import {
  getCookieName,
  getCookieOptions,
  getConfig,
  env,
} from "@thinkneverland/pixie-dust-config";
import { prisma } from "@thinkneverland/pixie-dust-database";
import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const pollingToken = url.searchParams.get("pollingToken");

  if (!pollingToken) {
    return NextResponse.redirect(
      `${env.APP_URL}/auth/login?error=${encodeURIComponent("Missing polling token.")}`,
    );
  }

  try {
    const result = await checkMagicLinkStatus(prisma, pollingToken);

    if (!result.verified) {
      return NextResponse.redirect(
        `${env.APP_URL}/auth/login?error=${encodeURIComponent("Link not yet verified.")}`,
      );
    }

    const ipAddress =
      req.headers.get("x-forwarded-for") ??
      req.headers.get("x-real-ip") ??
      undefined;
    const userAgent = req.headers.get("user-agent") ?? undefined;

    const session = await createSession(prisma, result.userId, {
      ipAddress,
      userAgent,
    });

    const dashboardUrl = `${env.APP_URL}/dashboard`;
    const appName = getConfig().appName;

    const html = `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta http-equiv="refresh" content="0;url=${dashboardUrl}"/>
<title>Signing in — ${appName}</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0a0a0a;color:#e2e2e8;font-family:system-ui,-apple-system,sans-serif}
p{font-size:14px;color:#888}</style></head>
<body><p>Signing you in…</p>
<script>window.location.replace(${JSON.stringify(dashboardUrl)});</script>
</body></html>`;

    const response = new NextResponse(html, {
      status: 200,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });

    response.cookies.set(getCookieName(), session.token, {
      ...getCookieOptions(),
      secure: env.NODE_ENV === "production",
    });

    return response;
  } catch {
    return NextResponse.redirect(
      `${env.APP_URL}/auth/login?error=${encodeURIComponent("Failed to create session.")}`,
    );
  }
}
