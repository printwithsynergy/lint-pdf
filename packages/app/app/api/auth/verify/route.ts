export const dynamic = "force-dynamic";

import {
  verifyMagicLink,
  createSession,
} from "@thinkneverland/pixie-dust-auth";
import {
  getCookieName,
  getCookieOptions,
  getConfig,
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

  const appConfig = getConfig();
  const appName = appConfig.appName ?? "LintPDF";
  const logoUrl = `${env.APP_URL}/logo-dark.svg`;

  const html = `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Verified — ${appName}</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0a0a0a;color:#fafafa;font-family:system-ui,-apple-system,sans-serif}
.card{text-align:center;max-width:400px;padding:3rem 2rem;border-radius:1rem;background:#111;border:1px solid #222}
.logo{width:48px;height:48px;margin:0 auto 1.5rem}
h1{font-size:1.5rem;font-weight:700;margin-bottom:.5rem}
p{font-size:.875rem;color:#888;line-height:1.5}
.check{width:64px;height:64px;margin:0 auto 1.5rem;border-radius:50%;background:#16a34a;display:flex;align-items:center;justify-content:center}
.check svg{width:32px;height:32px;color:#fff}</style></head>
<body><div class="card">
<div class="check"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg></div>
<img src="${logoUrl}" alt="${appName}" class="logo" onerror="this.style.display='none'"/>
<h1>You're Verified!</h1>
<p>You can close this tab and return to the original window — you'll be signed in automatically.</p>
</div></body></html>`;

  return new NextResponse(html, {
    status: 200,
    headers: { "Content-Type": "text/html" },
  });
}
