import { getConfig } from "@thinkneverland/pixie-dust-config";
import { evaluateMiddleware } from "@thinkneverland/pixie-dust-core/middleware";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

function getClientIp(request: NextRequest): string {
  return (
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
    request.headers.get("x-real-ip") ??
    "unknown"
  );
}

export function middleware(request: NextRequest) {
  const appConfig = getConfig();

  const result = evaluateMiddleware(
    {
      cookieName: appConfig.cookieName,
      rateLimitExemptPaths: [
        "/api/auth/magic-link/status",
        "/api/auth/claim-session",
      ],
    },
    {
      pathname: request.nextUrl.pathname,
      sessionCookie: request.cookies.get(appConfig.cookieName)?.value,
      clientIp: getClientIp(request),
      url: request.url,
    },
  );

  if (result.redirect) {
    const response = NextResponse.redirect(result.redirect);
    for (const [key, value] of Object.entries(result.headers)) {
      response.headers.set(key, value);
    }
    return response;
  }

  if (result.error) {
    return NextResponse.json(result.error.body, {
      status: result.error.status,
      headers: result.headers,
    });
  }

  const response = NextResponse.next();
  for (const [key, value] of Object.entries(result.headers)) {
    response.headers.set(key, value);
  }
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon\\.ico|favicon\\.png|favicon\\.svg|logo\\.png|logo\\.svg).*)"],
};
