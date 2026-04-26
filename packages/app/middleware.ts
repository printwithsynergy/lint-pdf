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
      // The interactive viewer at ``/view/{token}`` is public, but so are
      // the endpoints the client-side bundle hits once the page hydrates:
      // token validation, viewer config, page tiles, findings. If those
      // aren't explicitly public, a stale or invalid session cookie on an
      // iOS in-app browser trips the middleware and the fetch 401s — the
      // page then shows "Invalid or expired link" even though the token
      // is fine. Keep these patterns narrow: only the /public/ surfaces
      // that take a token as the authentication credential go in here.
      publicPaths: [
        "/view",
        "/api/waitlist",
        "/api/lintpdf/viewer/public",
        "/api/lintpdf/reports/tokens",
        // First-run Onboarding for the desktop and mobile apps —
        // resolves a tenant by name/slug/id/domain and returns the
        // branding blob to theme the app. Called before any user has
        // authenticated, so it must not require a session.
        "/api/public/tenant-lookup",
      ],
      rateLimitExemptPaths: [
        "/api/auth/magic-link/status",
        "/api/auth/claim-session",
        "/api/auth/mcp-backdoor",
        "/api/lintpdf",
        "/api/auth",
        "/api/trpc",
        "/api/waitlist",
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
  matcher: [
    "/((?!_next/static|_next/image|favicon\\.ico|favicon\\.png|favicon\\.svg|logo\\.png|logo\\.svg).*)",
  ],
};
